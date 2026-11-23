"""Importación de cambios OpenSpec como trabajos locales."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from unittest.mock import patch

from devforge_factory import lifecycle
from devforge_factory.core import FactoryError, create_job, git, init_project, read_job, transition
from devforge_factory.openspec import import_change
from support import symlinks_available


class OpenSpecAdapterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for args in (["init", "-b", "main"], ["-c", "user.name=QA", "-c", "user.email=qa@example.invalid",
                                             "commit", "--allow-empty", "-m", "base"]):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        init_project(self.root)

    def change(self, change_id="add-user-auth", proposal="# Autenticación de usuarios\n\n## Why\nHace falta login.\n"):
        folder = self.root / "openspec" / "changes" / change_id
        (folder / "specs" / "user-auth").mkdir(parents=True)
        (folder / "proposal.md").write_text(proposal, encoding="utf-8")
        (folder / "design.md").write_text("# Diseño\n\nUsar sesiones firmadas.\n", encoding="utf-8")
        (folder / "tasks.md").write_text("- [ ] Implementar login\n", encoding="utf-8")
        (folder / "specs" / "user-auth" / "spec.md").write_text("## ADDED Requirements\n\nLogin disponible.\n", encoding="utf-8")
        return folder

    def test_imports_change_with_all_artifacts(self):
        self.change()
        job = import_change(self.root, "add-user-auth")
        record = read_job(job)
        self.assertEqual(record["source"], "openspec")
        self.assertEqual(record["document"], "openspec/changes/add-user-auth")
        self.assertEqual(record["title"], "Autenticación de usuarios")
        self.assertTrue(record["branch"].startswith("feature/add-user-auth-autenticacion-de-usuarios"))
        request = (job / "request.md").read_text(encoding="utf-8")
        for expected in ("Cambio OpenSpec: add-user-auth", "proposal.md", "design.md",
                         "tasks.md", "specs/user-auth/spec.md", "Usar sesiones firmadas"):
            self.assertIn(expected, request)
        self.assertFalse((self.root / ".devforge" / "import-staging" / "openspec-add-user-auth.md").exists())

    def test_title_falls_back_to_first_prose_line(self):
        self.change(proposal="## Why\nUsuarios necesitan iniciar sesión.\n\n## What\nLogin.\n")
        record = read_job(import_change(self.root, "add-user-auth"))
        self.assertEqual(record["title"], "Usuarios necesitan iniciar sesión.")

    def test_missing_artifact_is_rejected(self):
        folder = self.change()
        (folder / "design.md").unlink()
        with self.assertRaisesRegex(FactoryError, "design.md"):
            import_change(self.root, "add-user-auth")

    def test_missing_specs_are_rejected(self):
        folder = self.change()
        shutil.rmtree(folder / "specs")
        with self.assertRaisesRegex(FactoryError, "specs"):
            import_change(self.root, "add-user-auth")

    def test_invalid_identifiers_are_rejected(self):
        for value in ("", "..", "a/b", "../fuera", "-inicio"):
            with self.assertRaisesRegex(FactoryError, "inválido"):
                import_change(self.root, value)

    @unittest.skipUnless(symlinks_available(), "este entorno no permite crear enlaces simbólicos")
    def test_symlinked_change_is_rejected(self):
        real = self.change("real")
        (self.root / "openspec" / "changes" / "alias").symlink_to(real)
        with self.assertRaisesRegex(FactoryError, "enlace"):
            import_change(self.root, "alias")

    @unittest.skipUnless(symlinks_available(), "este entorno no permite crear enlaces simbólicos")
    def test_symlinked_staging_is_rejected(self):
        self.change()
        outside = self.root / "outside"
        outside.mkdir()
        shutil.rmtree(self.root / ".devforge" / "import-staging")
        (self.root / ".devforge" / "import-staging").symlink_to(outside)
        with self.assertRaisesRegex(FactoryError, "enlace"):
            import_change(self.root, "add-user-auth")

    def test_branch_type_is_honored(self):
        self.change()
        record = read_job(import_change(self.root, "add-user-auth", branch_type="fix"))
        self.assertTrue(record["branch"].startswith("fix/add-user-auth-"))

    def _fake_cli(self):
        bindir = self.root / "bin"
        bindir.mkdir()
        binary = bindir / "openspec"
        binary.write_text(
            "#!/bin/sh\n"
            'printf "%s\\n" "$*" >> "$OPENSPEC_LOG"\n'
            'if [ "$1" = "validate" ] && [ -n "$OPENSPEC_FAIL" ] && [ -f "$OPENSPEC_FAIL" ]; then\n'
            '  echo "cambio inválido" >&2\n'
            "  exit 1\n"
            "fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)
        # Windows no ejecuta scripts de sh: el mismo CLI falso como archivo por lotes.
        (bindir / "openspec.cmd").write_text(
            "@echo off\n"
            '>>"%OPENSPEC_LOG%" echo %*\n'
            'if "%1"=="validate" if not "%OPENSPEC_FAIL%"=="" if exist "%OPENSPEC_FAIL%" (\n'
            "  echo cambio invalido 1>&2\n"
            "  exit /b 1\n"
            ")\n"
            "exit /b 0\n",
            encoding="utf-8",
        )
        log = self.root / "openspec.log"
        env = {"PATH": f"{bindir}{os.pathsep}{os.environ['PATH']}", "OPENSPEC_LOG": str(log), "OPENSPEC_FAIL": ""}
        return log, env

    def _review_job(self, source="openspec"):
        if source == "openspec":
            self.change()
            folder = import_change(self.root, "add-user-auth")
        else:
            folder = create_job(self.root, "direct", "Solicitud directa")
        worktree = Path(read_job(folder)["worktree"])
        git(worktree, "-c", "user.name=QA", "-c", "user.email=qa@example.invalid",
            "commit", "--allow-empty", "-m", "cambio implementado")
        transition(folder, "planned")
        transition(folder, "working")
        with patch.object(lifecycle, "run_gate", return_value=(True, "working-tree: PASS\ntest-command: PASS")):
            lifecycle.review(folder, read_job(folder), self.root)
        job = read_job(folder)
        sha = job["reviewed_sha"]
        for name in ("review-code.md", "review-security.md", "review-qa.md"):
            (folder / name).write_text(f"APTO\nHEAD: {sha}\n", encoding="utf-8")
        (folder / "decision.md").write_text(f"DECISION: APROBAR\nHEAD: {sha}\n", encoding="utf-8")
        return folder, sha

    def test_close_archives_and_syncs_the_change(self):
        log, env = self._fake_cli()
        folder, sha = self._review_job()
        with patch.dict(os.environ, env):
            with patch("builtins.input", return_value=f"CERRAR {folder.name} {sha[:12]}"):
                message = lifecycle.close(folder, read_job(folder))
        self.assertIn("sincronizado y archivado", message)
        record = read_job(folder)
        self.assertEqual(record["status"], "done")
        self.assertTrue(record["openspec_archived"])
        self.assertFalse(record["openspec_integrated"])
        calls = log.read_text(encoding="utf-8")
        self.assertIn("validate --strict add-user-auth", calls)
        self.assertIn("archive --yes add-user-auth", calls)

    def test_close_fails_when_validation_fails_and_keeps_the_job_open(self):
        _, env = self._fake_cli()
        folder, sha = self._review_job()
        env["OPENSPEC_FAIL"] = str(self.root / "openspec.log")
        with patch.dict(os.environ, env):
            with patch("builtins.input", return_value=f"CERRAR {folder.name} {sha[:12]}"):
                with self.assertRaisesRegex(FactoryError, "falló"):
                    lifecycle.close(folder, read_job(folder))
        self.assertEqual(read_job(folder)["status"], "review")

    def test_close_requires_the_openspec_cli(self):
        folder, sha = self._review_job()
        with patch("devforge_factory.openspec.shutil.which", return_value=None):
            with patch("builtins.input", return_value=f"CERRAR {folder.name} {sha[:12]}"):
                with self.assertRaisesRegex(FactoryError, "no está disponible"):
                    lifecycle.close(folder, read_job(folder))
        self.assertEqual(read_job(folder)["status"], "review")

    def test_direct_job_does_not_call_openspec(self):
        log, env = self._fake_cli()
        folder, sha = self._review_job(source="direct")
        with patch.dict(os.environ, env):
            with patch("builtins.input", return_value=f"CERRAR {folder.name} {sha[:12]}"):
                lifecycle.close(folder, read_job(folder))
        self.assertEqual(read_job(folder)["status"], "done")
        self.assertFalse(log.exists())

    def test_cli_entrypoint_imports_and_lists_the_job(self):
        self.change()
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        created = subprocess.run(
            [sys.executable, "-m", "devforge_factory.cli", "openspec", "add-user-auth"],
            cwd=self.root, env=env, capture_output=True, text=True, check=True,
        )
        self.assertIn("Trabajo creado", created.stdout)
        listed = subprocess.run(
            [sys.executable, "-m", "devforge_factory.cli", "ver"],
            cwd=self.root, env=env, capture_output=True, text=True, encoding="utf-8", check=True,
        )
        self.assertIn("Autenticación de usuarios", listed.stdout)
