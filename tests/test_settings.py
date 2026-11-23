"""Validación de la configuración de referencia de Claude Code."""

import json
from pathlib import Path
import unittest

SETTINGS = Path(__file__).resolve().parents[1] / ".claude" / "settings.json"


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SETTINGS.read_text(encoding="utf-8"))

    def test_credential_entries_use_schema_objects(self):
        credentials = self.data["sandbox"]["credentials"]
        self.assertTrue(credentials["envVars"])
        for entry in credentials["envVars"]:
            self.assertIsInstance(entry, dict)
            self.assertRegex(entry.get("name", ""), r"^[A-Z_][A-Z0-9_]*$")
            self.assertIn(entry.get("mode"), {"deny", "mask"})
        for entry in credentials["files"]:
            self.assertIsInstance(entry, dict)
            self.assertTrue(entry.get("path"))
            self.assertIn(entry.get("mode"), {"deny", "mask"})

    def test_reads_outside_project_do_not_prompt(self):
        # Evita confirmaciones en cada lectura fuera del proyecto; los secretos siguen en deny/denyRead.
        self.assertFalse(self.data["permissions"]["blockReadsOutsideWorkingDirectories"])

    def test_sandbox_fails_closed(self):
        sandbox = self.data["sandbox"]
        self.assertTrue(sandbox["enabled"])
        self.assertTrue(sandbox["failIfUnavailable"])
        self.assertFalse(sandbox["allowUnsandboxedCommands"])

    def test_devforge_runs_outside_claude_sandbox(self):
        # devforge crea worktrees y aísla sus tests con su propio bwrap.
        self.assertEqual(self.data["sandbox"]["excludedCommands"], ["devforge", "devforge *", "hc", "hc *"])
