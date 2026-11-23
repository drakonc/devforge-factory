import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devforge_factory import lifecycle
from devforge_factory.core import FactoryError, git, read_job, write_job
from support import symlinks_available


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / "job"
        self.folder.mkdir()
        self.tree = self.root / "work"
        self.tree.mkdir()
        git(self.tree, "init", "-b", "feature/prueba")
        git(self.tree, "-c", "user.name=Prueba", "-c", "user.email=x@example.invalid", "commit", "--allow-empty", "-m", "base")
        self.job = {"id": "DF-1", "status": "working", "branch": "feature/prueba",
                    "worktree": str(self.tree), "round": 1, "max_rounds": 2}
        write_job(self.folder, self.job)

    def gate(self, success):
        with patch.object(lifecycle, "run_gate", return_value=(success, "working-tree: PASS" if success else "gate: FAIL")):
            return lifecycle.review(self.folder, self.job, self.root)

    def test_failed_gate_rework_archive_and_exhaustion(self):
        for round_number in (1, 2):
            with self.assertRaisesRegex(FactoryError, "FAIL"):
                self.gate(False)
            self.assertTrue((self.folder / f"round-{round_number}/quality-gates.md").is_file())
            if round_number == 1:
                lifecycle.rework(self.folder, self.job)
            else:
                with self.assertRaisesRegex(FactoryError, "agotaron"):
                    lifecycle.rework(self.folder, self.job)
        self.assertEqual(read_job(self.folder)["status"], "blocked")
        with self.assertRaises(FactoryError):
            lifecycle.resume(self.folder, self.job)

    def test_pause_restores_review_and_close_requires_evidence_and_confirmation(self):
        self.gate(True)
        lifecycle.pause(self.folder, self.job)
        self.assertIn("revisión", lifecycle.resume(self.folder, self.job))
        self.assertEqual("review", read_job(self.folder)["status"])
        sha = self.job["reviewed_sha"]
        (self.folder / "intake.md").write_text("SUPERFICIES: interfaz\n")
        for name in (*lifecycle.MANDATORY, "decision.md"):
            first = "DECISION: APROBAR" if name == "decision.md" else "APTO"
            (self.folder / name).write_text(f"{first}\nHEAD: {sha}\n")
        with self.assertRaisesRegex(FactoryError, "review-ui"):
            lifecycle.close(self.folder, self.job)
        for name in lifecycle.VISUAL:
            (self.folder / name).write_text(f"APTO\nHEAD: {sha}\n")
        with patch("builtins.input", return_value=""):
            with self.assertRaisesRegex(FactoryError, "cancelado"):
                lifecycle.close(self.folder, self.job)
        self.assertEqual(read_job(self.folder)["status"], "review")
        with patch("builtins.input", return_value=f"CERRAR DF-1 {sha[:12]}"):
            lifecycle.close(self.folder, self.job)
        self.assertEqual(read_job(self.folder)["status"], "done")
        self.assertTrue((self.folder / "round-1/decision.md").is_file())

    def test_stale_sha_and_pause_rework_cannot_bypass_review(self):
        self.gate(True)
        git(self.tree, "-c", "user.name=Prueba", "-c", "user.email=x@example.invalid", "commit", "--allow-empty", "-m", "nuevo")
        with self.assertRaisesRegex(FactoryError, "SHA"):
            lifecycle.acceptance(self.folder, self.job)
        lifecycle.rework(self.folder, self.job)
        self.assertIsNone(self.job["reviewed_sha"])
        self.assertFalse((self.folder / "quality-gates.md").exists())

    def test_second_holder_cannot_lock_the_job(self):
        with lifecycle.job_lock(self.folder):
            with self.assertRaisesRegex(FactoryError, "Otro proceso"):
                with lifecycle.job_lock(self.folder):
                    pass

    @unittest.skipUnless(symlinks_available(), "este entorno no permite crear enlaces simbólicos")
    def test_lock_symlink_is_rejected(self):
        outside = self.root / "outside.lock"
        outside.write_text("x", encoding="utf-8")
        (self.folder / ".lifecycle.lock").symlink_to(outside)
        with self.assertRaisesRegex(FactoryError, "enlace simbólico"):
            with lifecycle.job_lock(self.folder):
                pass

    def test_rework_after_publication_is_blocked(self):
        self.gate(True)
        job = read_job(self.folder)
        job["pull_request"] = "https://github.com/org/repo/pull/1"
        write_job(self.folder, job)
        with self.assertRaisesRegex(FactoryError, "publicar"):
            lifecycle.rework(self.folder, job)
