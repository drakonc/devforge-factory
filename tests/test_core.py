import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devforge_factory.core import FactoryError, create_job, extract_file, init_project, normalize, publish_draft_pr, run_gate, slugify, transition, write_job


class CoreTests(unittest.TestCase):
    def _publishable_job(self, root: Path, remote: str = "https://github.com/org/repo.git") -> tuple[Path, Path]:
        folder = root / "job"
        folder.mkdir()
        worktree = root / "worktree"
        worktree.mkdir()
        write_job(folder, {"id": "DF-123-test", "status": "review", "worktree": str(worktree), "branch": "feature/df-123-test", "base_branch": "develop", "title": "Test", "pull_request": None, "reviewed_sha": "abc123", "quality_gates": ["git-diff-check", "tests-configured", "human-approval"]})
        (folder / "quality-gates.md").write_text("working-tree: PASS\ngit diff --check: PASS\ntest-command: PASS\nhuman-approval: PENDING\n", encoding="utf-8")
        for report in ("review-code.md", "review-security.md", "review-qa.md"):
            (folder / report).write_text("APTO\nHEAD: abc123\n", encoding="utf-8")
        return folder, worktree

    def test_normalize_extracts_title_and_preserves_body(self):
        request = normalize("direct", "# Agregar búsqueda\n\nDebe filtrar por nombre.")
        self.assertEqual(request["title"], "Agregar búsqueda")
        self.assertIn("Debe filtrar por nombre", request["description"])

    def test_pdf_extraction_stops_when_output_limit_is_exceeded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf = root / "input.pdf"
            pdf.write_bytes(b"pdf")
            extractor = root / "pdftotext"
            extractor.write_text("#!/usr/bin/env python3\nimport sys\nsys.stdout.buffer.write(b'x' * (11 * 1024 * 1024))\n", encoding="utf-8")
            extractor.chmod(0o755)
            with patch("devforge_factory.core.shutil.which", return_value=str(extractor)):
                with self.assertRaisesRegex(FactoryError, "10 MiB"):
                    extract_file(pdf)

    def test_slugify_limits_untrusted_title_to_safe_characters(self):
        self.assertEqual(slugify("../../ A B! "), "a-b")

    def test_transition_persists_valid_state(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            write_job(folder, {"id": "DF-1", "status": "queued"})
            result = transition(folder, "planned")
            self.assertEqual(result["status"], "planned")
            self.assertEqual(json.loads((folder / "job.json").read_text())["status"], "planned")

    def test_transition_rejects_invalid_state_change(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            write_job(folder, {"id": "DF-1", "status": "queued"})
            with self.assertRaises(FactoryError):
                transition(folder, "done")

    def test_create_job_uses_isolated_worktree_and_expected_branch(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-b", "develop"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-m", "base"], cwd=root, check=True, capture_output=True)
            init_project(root)
            job = create_job(root, "direct", "Agregar búsqueda", "DF-123")
            record = json.loads((job / "job.json").read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "queued")
            self.assertEqual(record["branch"], "feature/df-123-agregar-busqueda")
            self.assertTrue(Path(record["worktree"]).is_dir())
            self.assertEqual(record["base_branch"], "develop")
            self.assertEqual(record["test_command"], [])
            self.assertEqual(record["test_env"], [])

    def test_quality_gate_does_not_inherit_secrets_unless_allowlisted(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-b", "develop"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "--allow-empty", "-m", "base"], cwd=root, check=True, capture_output=True)
            init_project(root)
            worktree = root / ".devforge" / "worktrees" / "test-worktree"
            subprocess.run(["git", "worktree", "add", "-b", "feature/test", str(worktree), "develop"], cwd=root, check=True, capture_output=True)
            secret_file = Path(temp) / "host-secret.txt"
            secret_file.write_text("must stay outside sandbox", encoding="utf-8")
            job = {"worktree": str(worktree), "base_branch": "develop", "quality_gates": ["tests-configured"], "test_command": ["python3", "-c", f"import os,sys; from pathlib import Path; sys.exit(1 if 'DEVFORGE_SECRET_TEST' in os.environ or Path({str(secret_file)!r}).exists() else 0)"], "test_env": []}
            with patch.dict("os.environ", {"DEVFORGE_SECRET_TEST": "secret-value"}):
                okay, _ = run_gate(root, job)
            self.assertTrue(okay)
            job["test_command"] = ["python3", "-c", "import os,sys; sys.exit(0 if os.getenv('DEVFORGE_TEST_ALLOWED') == 'available' else 1)"]
            job["test_env"] = ["DEVFORGE_TEST_ALLOWED"]
            with patch.dict("os.environ", {"DEVFORGE_TEST_ALLOWED": "available"}):
                okay, _ = run_gate(root, job)
            self.assertTrue(okay)
            with patch("devforge_factory.core.shutil.which", return_value=None):
                okay, report = run_gate(root, job)
            self.assertFalse(okay)
            self.assertIn("bwrap", report)

    def test_init_does_not_overwrite_existing_project_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            target = root / ".devforge" / "project.yaml"
            target.parent.mkdir()
            target.write_text("profile: custom\n", encoding="utf-8")
            with self.assertRaises(FactoryError):
                init_project(root)
            self.assertEqual(target.read_text(encoding="utf-8"), "profile: custom\n")

    def test_init_rejects_broken_symlink_for_project_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
            target = root / ".devforge" / "project.yaml"
            target.parent.mkdir()
            target.symlink_to(Path(temp) / "outside.yaml")
            with self.assertRaises(FactoryError):
                init_project(root)
            self.assertFalse((Path(temp) / "outside.yaml").exists())

    def test_external_import_uses_integrated_content_and_source_metadata(self):
        from types import SimpleNamespace
        from devforge_factory.cli import create_from

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            staging = root / ".devforge" / "import-staging"
            staging.mkdir(parents=True)
            imported = staging / "import-abc123.md"
            imported.write_text("Resumen del ticket\n\nDetalle importado", encoding="utf-8")
            args = SimpleNamespace(file=str(imported), url=None, stdin=False, request=None, source="jira", key="ABC-123")
            with patch("devforge_factory.cli.Path.cwd", return_value=root):
                with patch("devforge_factory.cli.config_for", return_value=(root, {})):
                    with patch("devforge_factory.cli.create_job", return_value=root / ".devforge/jobs/abc-123-resumen") as create:
                        create_from(args)
            self.assertEqual(create.call_args.args, (root, "jira", "Resumen del ticket\n\nDetalle importado", "ABC-123"))
            self.assertFalse(imported.exists())

    def test_cli_rejects_remote_url_fetch(self):
        from types import SimpleNamespace
        from devforge_factory.cli import create_from

        args = SimpleNamespace(file=None, url="https://github.com/org/repo/issues/1", stdin=False, request=None, source=None, key="")
        with self.assertRaisesRegex(FactoryError, "no consulta servicios remotos"):
            create_from(args)

    def test_publication_requires_exact_human_confirmation_before_push(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temp:
            folder, worktree = self._publishable_job(Path(temp))
            with patch("devforge_factory.core.project_root", return_value=Path(temp)):
                with patch("devforge_factory.core.git", side_effect=[
                    SimpleNamespace(returncode=0, stdout="feature/df-123-test\n"),
                    SimpleNamespace(returncode=0, stdout="abc123\n"),
                    SimpleNamespace(returncode=0, stdout=""),
                    SimpleNamespace(returncode=0, stdout="1\n"),
                    SimpleNamespace(returncode=0, stdout="https://github.com/org/repo.git\n"),
                ]):
                    with patch("devforge_factory.core.subprocess.run", return_value=SimpleNamespace(returncode=0, stdout="")) as run:
                        with patch("builtins.input", return_value="NO"):
                            with self.assertRaises(FactoryError):
                                publish_draft_pr(folder)
                        self.assertEqual(run.call_count, 2)
                        self.assertEqual(run.call_args_list[0].args[0], ["gh", "auth", "status"])

    def test_publication_binds_approval_to_reviewed_head_and_remote(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temp:
            folder, _ = self._publishable_job(Path(temp))
            remote = "https://github.com/org/repo.git"
            git_results = [
                SimpleNamespace(returncode=0, stdout="feature/df-123-test\n"),
                SimpleNamespace(returncode=0, stdout="abc123\n"),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="1\n"),
                SimpleNamespace(returncode=0, stdout=remote + "\n"),
                SimpleNamespace(returncode=0, stdout=remote + "\n"),
                SimpleNamespace(returncode=0, stdout="abc123\n"),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="feature/df-123-test\n"),
                SimpleNamespace(returncode=0, stdout="abc123\trefs/heads/feature/df-123-test\n"),
            ]
            gh_results = [
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=1, stdout=""),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="https://github.com/org/repo/pull/9\n"),
                SimpleNamespace(returncode=0, stdout="abc123\n"),
            ]
            with patch("devforge_factory.core.git", side_effect=git_results):
                with patch("devforge_factory.core.run_gate", return_value=(True, "PASS")):
                    with patch("devforge_factory.core.shutil.which", return_value="/usr/bin/gh"):
                        with patch("devforge_factory.core.subprocess.run", side_effect=gh_results) as run:
                            phrase = f"PUBLICAR DF-123-test abc123 {remote}"
                            with patch("builtins.input", return_value=phrase) as prompt:
                                result = publish_draft_pr(folder)
            self.assertEqual(result, "https://github.com/org/repo/pull/9")
            self.assertEqual(run.call_args_list[2].args[0], ["git", "push", remote, "abc123:refs/heads/feature/df-123-test"])
            self.assertEqual(json.loads((folder / "job.json").read_text())["pull_request"], result)

    def test_publication_aborts_if_remote_changes_after_approval(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temp:
            folder, _ = self._publishable_job(Path(temp))
            remote = "https://github.com/org/repo.git"
            git_results = [
                SimpleNamespace(returncode=0, stdout="feature/df-123-test\n"),
                SimpleNamespace(returncode=0, stdout="abc123\n"),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="1\n"),
                SimpleNamespace(returncode=0, stdout=remote + "\n"),
                SimpleNamespace(returncode=0, stdout="https://attacker.example/repo.git\n"),
                SimpleNamespace(returncode=0, stdout="abc123\n"),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="feature/df-123-test\n"),
            ]
            gh_results = [SimpleNamespace(returncode=0, stdout=""), SimpleNamespace(returncode=1, stdout="")]
            with patch("devforge_factory.core.git", side_effect=git_results):
                with patch("devforge_factory.core.run_gate", return_value=(True, "PASS")):
                    with patch("devforge_factory.core.shutil.which", return_value="/usr/bin/gh"):
                        with patch("devforge_factory.core.subprocess.run", side_effect=gh_results) as run:
                            with patch("builtins.input", return_value=f"PUBLICAR DF-123-test abc123 {remote}"):
                                with self.assertRaises(FactoryError):
                                    publish_draft_pr(folder)
            self.assertEqual(run.call_count, 2)

    def test_publication_records_but_does_not_accept_pr_with_different_head(self):
        from types import SimpleNamespace

        with tempfile.TemporaryDirectory() as temp:
            folder, _ = self._publishable_job(Path(temp))
            remote = "https://github.com/org/repo.git"
            git_results = [
                SimpleNamespace(returncode=0, stdout="feature/df-123-test\n"),
                SimpleNamespace(returncode=0, stdout="abc123\n"),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="1\n"),
                SimpleNamespace(returncode=0, stdout=remote + "\n"),
                SimpleNamespace(returncode=0, stdout=remote + "\n"),
                SimpleNamespace(returncode=0, stdout="abc123\n"),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="feature/df-123-test\n"),
                SimpleNamespace(returncode=0, stdout="abc123\trefs/heads/feature/df-123-test\n"),
            ]
            gh_results = [
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=1, stdout=""),
                SimpleNamespace(returncode=0, stdout=""),
                SimpleNamespace(returncode=0, stdout="https://github.com/org/repo/pull/10\n"),
                SimpleNamespace(returncode=0, stdout="deadbeef\n"),
            ]
            with patch("devforge_factory.core.git", side_effect=git_results):
                with patch("devforge_factory.core.run_gate", return_value=(True, "PASS")):
                    with patch("devforge_factory.core.shutil.which", return_value="/usr/bin/gh"):
                        with patch("devforge_factory.core.subprocess.run", side_effect=gh_results) as run:
                            phrase = f"PUBLICAR DF-123-test abc123 {remote}"
                            with patch("builtins.input", return_value=phrase):
                                with self.assertRaises(FactoryError):
                                    publish_draft_pr(folder)
            self.assertEqual(run.call_count, 5)
            record = json.loads((folder / "job.json").read_text(encoding="utf-8"))
            self.assertTrue(record["pull_request_head_mismatch"])
            self.assertEqual(record["status"], "blocked")
            self.assertEqual(record["pull_request"], "https://github.com/org/repo/pull/10")
            with self.assertRaises(FactoryError):
                publish_draft_pr(folder)

    def test_publication_rejects_any_failed_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / "job"
            folder.mkdir()
            write_job(folder, {"id": "DF-123-test", "status": "review", "quality_gates": ["git-diff-check", "tests-configured"]})
            (folder / "quality-gates.md").write_text("git diff --check: PASS\ntest-command: FAIL (exit code 1)\n", encoding="utf-8")
            with self.assertRaises(FactoryError):
                publish_draft_pr(folder)

    def test_publication_rejects_unknown_quality_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            folder, _ = self._publishable_job(Path(temp))
            job = json.loads((folder / "job.json").read_text(encoding="utf-8"))
            job["quality_gates"].append("test-comand")
            write_job(folder, job)
            with self.assertRaises(FactoryError):
                publish_draft_pr(folder)

    def test_publication_rejects_stale_review_report(self):
        with tempfile.TemporaryDirectory() as temp:
            folder, _ = self._publishable_job(Path(temp))
            (folder / "review-code.md").write_text("APTO\nHEAD: old-sha\n", encoding="utf-8")
            with self.assertRaises(FactoryError):
                publish_draft_pr(folder)


if __name__ == "__main__":
    unittest.main()
