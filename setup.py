"""Empaqueta la skill y los agentes junto al CLI."""

from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py

ROOT = Path(__file__).parent


class build_py(_build_py):
    def run(self):
        super().run()
        target = Path(self.build_lib) / "devforge_factory" / "resources"
        shutil.copytree(ROOT / ".claude" / "skills" / "factory", target / "skills" / "factory", dirs_exist_ok=True)
        shutil.copytree(ROOT / ".claude" / "agents", target / "agents", dirs_exist_ok=True)
        shutil.copy2(ROOT / ".claude" / "settings.json", target / "settings.json")


setup(cmdclass={"build_py": build_py})
