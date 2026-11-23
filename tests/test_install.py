"""Instalación de la skill y los agentes a nivel de usuario."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from devforge_factory.install import install_global
from support import IS_WINDOWS

SANDBOX_SKIP = "el bloque sandbox no se instala en Windows nativo"


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

    @unittest.skipUnless(IS_WINDOWS, "comportamiento específico de Windows")
    def test_windows_settings_omit_the_sandbox_that_would_stop_claude_code(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                message = install_global()
            data = json.loads((Path(temp) / "settings.json").read_text(encoding="utf-8"))
            self.assertNotIn("sandbox", data)
            self.assertFalse(data["permissions"]["blockReadsOutsideWorkingDirectories"])
            self.assertIn("Windows nativo", message)

    @unittest.skipUnless(IS_WINDOWS, "comportamiento específico de Windows")
    def test_windows_merge_adds_permissions_and_leaves_user_sandbox_alone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = {"keep": True, "sandbox": {"excludedCommands": ["docker"]}}
            (root / "settings.json").write_text(json.dumps(existing), encoding="utf-8")
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                message = install_global()
                again = install_global()
            data = json.loads((root / "settings.json").read_text(encoding="utf-8"))
            self.assertIn("añadido", message)
            self.assertIn("ya contiene", again)
            self.assertTrue(data["keep"])
            self.assertEqual(data["sandbox"], {"excludedCommands": ["docker"]})
            self.assertIn("Read(./.env)", data["permissions"]["deny"])
            self.assertEqual(json.loads((root / "settings.json.bak").read_text(encoding="utf-8")), existing)

    @unittest.skipIf(IS_WINDOWS, SANDBOX_SKIP)
    def test_existing_settings_keep_values_and_gain_missing_ones(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = {
                "keep": True,
                "sandbox": {
                    "allowUnsandboxedCommands": True,
                    "excludedCommands": ["docker"],
                    "credentials": {"envVars": [{"name": "GH_TOKEN", "mode": "mask"}]},
                },
            }
            (root / "settings.json").write_text(json.dumps(existing), encoding="utf-8")
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                message = install_global()
                again = install_global()
            data = json.loads((root / "settings.json").read_text(encoding="utf-8"))
            sandbox = data["sandbox"]
            self.assertIn("añadido", message)
            self.assertIn("allowUnsandboxedCommands", message)
            self.assertIn("ya contiene", again)
            self.assertTrue(data["keep"])
            self.assertTrue(sandbox["allowUnsandboxedCommands"])
            self.assertTrue(sandbox["enabled"])
            self.assertEqual(sandbox["excludedCommands"], ["docker", "devforge", "devforge *"])
            gh = [entry for entry in sandbox["credentials"]["envVars"] if entry["name"] == "GH_TOKEN"]
            self.assertEqual(gh, [{"name": "GH_TOKEN", "mode": "mask"}])
            self.assertIn({"name": "GITHUB_TOKEN", "mode": "deny"}, sandbox["credentials"]["envVars"])
            self.assertIn("files", sandbox["credentials"])

    def test_invalid_settings_are_left_untouched(self):
        for content in ("{no es json", "[]", '"texto"'):
            with self.subTest(content=content), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                (root / "settings.json").write_text(content, encoding="utf-8")
                with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                    message = install_global()
                self.assertIn("no es un objeto JSON legible", message)
                self.assertEqual((root / "settings.json").read_text(encoding="utf-8"), content)

    @unittest.skipIf(IS_WINDOWS, SANDBOX_SKIP)
    def test_merge_backs_up_once_and_second_run_does_not_rewrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = '{\n    "sandbox": {"excludedCommands": ["devforge"]}\n}\n'
            (root / "settings.json").write_text(original, encoding="utf-8")
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                install_global()
                merged = (root / "settings.json").read_bytes()
                install_global()
            self.assertEqual((root / "settings.json.bak").read_text(encoding="utf-8"), original)
            self.assertEqual((root / "settings.json").read_bytes(), merged)
            data = json.loads(merged)
            self.assertEqual(data["sandbox"]["excludedCommands"], ["devforge", "devforge *"])
            self.assertFalse((root / "settings.json.tmp").exists())

    @unittest.skipIf(IS_WINDOWS, SANDBOX_SKIP)
    def test_script_merge_works_without_pyyaml(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            stub = Path(temp) / "stub"
            stub.mkdir()
            (stub / "yaml.py").write_text("raise ImportError('sin PyYAML')\n", encoding="utf-8")
            target = Path(temp) / "settings.json"
            target.write_text("{}", encoding="utf-8")
            # Mismo one-liner que scripts/instalar-global.sh, con un yaml que falla al importarse.
            code = ("import sys; from pathlib import Path; from devforge_factory.install import _merge_settings; "
                    "print('Settings:', _merge_settings(Path(sys.argv[1]), Path(sys.argv[2])))")
            env = dict(os.environ, PYTHONPATH=f"{stub}{os.pathsep}{repo}")
            result = subprocess.run([sys.executable, "-c", code, str(repo / ".claude" / "settings.json"), str(target)],
                                    env=env, capture_output=True, text=True, check=True)
            self.assertIn("añadido", result.stdout)
            self.assertIn("devforge *", json.loads(target.read_text(encoding="utf-8"))["sandbox"]["excludedCommands"])

    @unittest.skipIf(IS_WINDOWS, SANDBOX_SKIP)
    def test_mismatched_types_keep_user_value(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "settings.json").write_text('{"sandbox": []}', encoding="utf-8")
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": temp}):
                message = install_global()
            data = json.loads((root / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(data["sandbox"], [])
            self.assertIn("se conservan tus valores en: sandbox", message)

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
