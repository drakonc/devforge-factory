"""Recorrido local completo con un work item de ejemplo y gates reales."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

from support import bwrap_ready


class DeliveryFlowTests(unittest.TestCase):
    @unittest.skipUnless(bwrap_ready(), "bwrap no puede crear el sandbox en este entorno")
    def test_boards_to_local_close_and_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
            def run(*args, cwd=root, stdin=None, check=True):
                return subprocess.run(args, cwd=cwd, env=env, input=stdin, capture_output=True,
                                      text=True, check=check)
            def cli(*args, **kwargs):
                return run(sys.executable, "-m", "devforge_factory.cli", *args, **kwargs)

            run("git", "init", "-b", "develop")
            run("git", "config", "user.name", "Prueba")
            run("git", "config", "user.email", "prueba@example.invalid")
            run("git", "commit", "--allow-empty", "-m", "base")
            run("git", "remote", "add", "origin", "git@ssh.dev.azure.com:v3/empresa/ventas/api")
            self.assertEqual(cli("repo").stdout.strip(), "https://dev.azure.com/empresa/ventas/_git/api")
            cli("init")
            config = root / ".devforge/project.yaml"
            settings = yaml.safe_load(config.read_text())
            settings["test_command"] = ["python3", "-c", "from pathlib import Path; assert Path('total.txt').read_text() == '10'"]
            config.write_text(yaml.safe_dump(settings))
            cli("hacer", "--source", "azure", "--key", "AB-123", "--type", "fix", "--stdin",
                stdin="Corregir total")
            job_id = cli("tomar").stdout.strip()
            folder = root / ".devforge/jobs" / job_id
            def job():
                return json.loads((folder / "job.json").read_text())
            tree = Path(job()["worktree"])
            cli("plan", job_id)
            cli("seguir", job_id)
            self.assertNotEqual(cli("revisar", job_id, check=False).returncode, 0)
            cli("rework", job_id)
            self.assertEqual(job()["round"], 2)
            (tree / "total.txt").write_text("10")
            run("git", "add", "total.txt", cwd=tree)
            run("git", "commit", "-m", "fix: corregir total", cwd=tree)
            cli("revisar", job_id)
            sha = job()["reviewed_sha"]
            cli("parar", job_id)
            cli("seguir", job_id)
            self.assertEqual(job()["status"], "review")
            for report in ("review-code", "review-security", "review-qa", "decision"):
                verdict = "DECISION: APROBAR" if report == "decision" else "APTO"
                (folder / f"{report}.md").write_text(f"{verdict}\nHEAD: {sha}\n")
            cli("cerrar", job_id, stdin=f"CERRAR {job_id} {sha[:12]}\n")
            cli("liberar", job_id)
            self.assertEqual(job()["status"], "done")
            self.assertIn("done", Path(cli("dashboard").stdout.strip()).read_text())
            self.assertTrue((folder / "round-1/quality-gates.md").exists())
            self.assertTrue((folder / "round-2/decision.md").exists())
