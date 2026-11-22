"""Validación de reservas concurrentes, tablero y Azure Repos sin red."""

import concurrent.futures
import contextlib
import io
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

from devforge_factory.board import claim_next, dashboard, release, show_queue
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

    def _leases(self):
        return self.root / ".devforge" / "jobs" / ".reservas.json"

    def _set_lease(self, job_id, hours_ago):
        stamp = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        self._leases().write_text(json.dumps({job_id: stamp}) + "\n", encoding="utf-8")

    def _config(self):
        return self.root / ".devforge" / "project.yaml"

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

    def test_expired_reservation_is_released_and_reclaimable(self):
        job_id = create_job(self.root, "direct", "Tarea abandonada").name
        self.assertEqual(claim_next(self.root), job_id)
        self._set_lease(job_id, hours_ago=13)
        stale = json.loads(self._leases().read_text())[job_id]
        self.assertEqual(claim_next(self.root), job_id)
        renewed = json.loads(self._leases().read_text())[job_id]
        self.assertGreater(datetime.fromisoformat(renewed), datetime.fromisoformat(stale))

    def test_fresh_reservation_is_respected(self):
        job_id = create_job(self.root, "direct", "Tarea en curso").name
        self.assertEqual(claim_next(self.root), job_id)
        self._set_lease(job_id, hours_ago=1)
        with self.assertRaisesRegex(FactoryError, "sin reservar"):
            claim_next(self.root)

    def test_queue_reports_expired_reservations(self):
        job_id = create_job(self.root, "direct", "Tarea caída").name
        claim_next(self.root)
        self._set_lease(job_id, hours_ago=24)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            show_queue(self.root)
        self.assertIn("caducadas liberadas: 1", output.getvalue())

    def test_malformed_reservation_record_is_rejected(self):
        create_job(self.root, "direct", "Tarea con registro roto")
        self._leases().write_text('{"x": "no-es-fecha"}\n', encoding="utf-8")
        with self.assertRaisesRegex(FactoryError, "fecha inválida"):
            claim_next(self.root)

    def test_invalid_ttl_is_rejected(self):
        create_job(self.root, "direct", "Tarea con TTL inválido")
        settings = yaml.safe_load(self._config().read_text())
        settings["reservation_ttl_hours"] = 0
        self._config().write_text(yaml.safe_dump(settings))
        with self.assertRaisesRegex(FactoryError, "reservation_ttl_hours"):
            claim_next(self.root)

    def test_dashboard_refreshes_and_shows_round_budget(self):
        create_job(self.root, "direct", "Tarea visible")
        page = dashboard(self.root).read_text(encoding="utf-8")
        self.assertIn('http-equiv="refresh"', page)
        self.assertIn("1/3", page)

    def test_azure_https_ssh_and_invalid_segments(self):
        canonical = "https://dev.azure.com/org/Proyecto%20A/_git/app"
        self.assertEqual(azure_repository(canonical), canonical)
        self.assertEqual(azure_repository("git@ssh.dev.azure.com:v3/org/Proyecto%20A/app"), canonical)
        self.assertEqual(azure_repository(canonical.replace("https://", "https://org@")), canonical)
        for invalid in ("%2e%2e", "%2Fetc", "app?key=1", "%0A"):
            with self.assertRaises(FactoryError):
                azure_repository(f"https://dev.azure.com/org/team/_git/{invalid}")
