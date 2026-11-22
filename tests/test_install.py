"""Instalación de la skill y los agentes a nivel de usuario."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from devforge_factory.install import install_global


class InstallGlobalTests(unittest.TestCase):
    def test_installs_skill_agents_and_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                message = install_global()
            root = Path(temp)
            self.assertIn("Agentes: 9", message)
            self.assertTrue((root / "skills" / "factory" / "SKILL.md").is_file())
            self.assertEqual(len(list((root / "agents").glob("devforge-*.md"))), 9)
            self.assertTrue((root / "settings.json").is_file())

    def test_does_not_overwrite_existing_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "settings.json").write_text('{"keep": true}\n', encoding="utf-8")
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                message = install_global()
            self.assertIn("existe", message)
            self.assertEqual((root / "settings.json").read_text(encoding="utf-8"), '{"keep": true}\n')

    def test_second_run_refreshes_copied_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                install_global()
                agent = Path(temp) / "agents" / "devforge-builder.md"
                agent.write_text("modificado\n", encoding="utf-8")
                install_global()
            self.assertNotEqual(agent.read_text(encoding="utf-8"), "modificado\n")

    def test_cli_entrypoint_runs_the_installation(self):
        with tempfile.TemporaryDirectory() as temp:
            env = dict(os.environ, CLAUDE_CONFIG_DIR=temp, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
            result = subprocess.run([sys.executable, "-m", "devforge_factory.cli", "instalar-global"],
                                    cwd=Path(temp), env=env, capture_output=True, text=True, check=True)
            self.assertIn("Agentes: 9", result.stdout)
            self.assertTrue((Path(temp) / "skills" / "factory" / "SKILL.md").is_file())
