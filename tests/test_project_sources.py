"""Pruebas de las entradas de la fábrica desde un repositorio consumidor."""

import contextlib
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

from devforge_factory.cli import create_from, parser
from devforge_factory.core import FactoryError, document_paths, init_project, jobs, repository_slug


class ProjectSourcesTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-b", "main")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-m", "base")
        init_project(self.root)

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=True)

    def test_cli_entrypoint_accepts_hacer_and_lists_the_job(self):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        for args in (["hacer", "Filtro por fecha"], ["ver"]):
            result = subprocess.run([sys.executable, "-m", "devforge_factory.cli", *args],
                                    cwd=self.root, env=env, capture_output=True, text=True, check=True)
        self.assertIn("Filtro por fecha", result.stdout)

    def test_cli_reports_version_for_support(self):
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        result = subprocess.run([sys.executable, "-m", "devforge_factory.cli", "--version"],
                                cwd=self.root, env=env, capture_output=True, text=True, check=True)
        self.assertRegex(result.stdout.strip(), r"^devforge \d+\.\d+\.\d+$")

    def test_identifies_current_repo_without_reading_an_account(self):
        self.git("remote", "add", "origin", "git@github.com:equipo/proyecto.git")
        self.assertEqual(repository_slug(self.root), "equipo/proyecto")
        self.git("remote", "set-url", "origin", "https://gitlab.com/equipo/proyecto.git")
        with self.assertRaises(FactoryError):
            repository_slug(self.root)

    def test_document_from_subdirectory_preserves_original_and_origin(self):
        docs = self.root / "docs"
        docs.mkdir()
        file = docs / "Requisito de búsqueda.md"
        file.write_text("# Búsqueda\nEncontrar por nombre.", encoding="utf-8")
        history = docs / "requerimientio"
        history.mkdir()
        (history / "anterior.md").touch()
        self.assertEqual(document_paths(docs), ["docs/Requisito de búsqueda.md"])
        with contextlib.chdir(docs):
            create_from(parser().parse_args(["hacer", "--file", file.name]))
        record = jobs(self.root)[0][1]
        self.assertEqual(record["document"], "docs/Requisito de búsqueda.md")
        self.assertEqual(record["base_branch"], "main")
        self.assertNotIn("profile", record)
        self.assertTrue(file.is_file())

    def test_jira_github_and_text_share_the_same_configuration(self):
        with contextlib.chdir(self.root):
            for source in ("jira", "github", "direct"):
                create_from(parser().parse_args(["hacer", "Solicitud " + source, "--source", source]))
        self.assertEqual({job["source"] for _, job in jobs(self.root)}, {"jira", "github", "direct"})
