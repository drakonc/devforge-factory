"""Validación de reservas concurrentes, tablero y Azure Repos sin red."""

import concurrent.futures
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from devforge_factory.board import claim_next, dashboard, release
from devforge_factory.core import FactoryError, azure_repository, create_job, init_project, read_job


class BoardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for args in (["init", "-b", "main"], ["-c", "user.name=QA", "-c", "user.email=qa@example.invalid",
                                             "commit", "--allow-empty", "-m", "base"]):
            subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)
        init_project(self.root)

    def test_concurrent_processes_respect_capacity_and_reserve_distinct_jobs(self):
        for n in range(3):
            create_job(self.root, "direct", f"Tarea {n}")
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        def claim(_):
            return subprocess.run([sys.executable, "-m", "devforge_factory.cli", "tomar"],
                                  cwd=self.root, env=env, capture_output=True, text=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(claim, range(3)))
        accepted = [r.stdout.strip() for r in results if r.returncode == 0]
        self.assertEqual(len(accepted), 2, [r.stderr for r in results])
        self.assertEqual(len(set(accepted)), 2)
        with self.assertRaises(FactoryError):
            claim_next(self.root)
        release(self.root, accepted[0])
        self.assertNotEqual(claim_next(self.root), accepted[1])

    def test_dashboard_escapes_titles_and_omits_request_bodies(self):
        folder = create_job(self.root, "azure", "<script>fallo</script>\nDetalle privado", "AB-42", branch_type="fix")
        self.assertTrue(read_job(folder)["branch"].startswith("fix/ab-42-"))
        page = dashboard(self.root).read_text()
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("Detalle privado", page)
        self.assertNotIn("<script>", page)

    def test_azure_https_ssh_and_invalid_segments(self):
        canonical = "https://dev.azure.com/org/Proyecto%20A/_git/app"
        self.assertEqual(azure_repository(canonical), canonical)
        self.assertEqual(azure_repository("git@ssh.dev.azure.com:v3/org/Proyecto%20A/app"), canonical)
        self.assertEqual(azure_repository(canonical.replace("https://", "https://org@")), canonical)
        for invalid in ("%2e%2e", "%2Fetc", "app?key=1", "%0A"):
            with self.assertRaises(FactoryError):
                azure_repository(f"https://dev.azure.com/org/team/_git/{invalid}")
