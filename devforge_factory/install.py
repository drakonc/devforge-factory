"""Instalación de la skill y los agentes en la configuración del usuario."""

import os
import shutil
from pathlib import Path

from .core import FactoryError


def _resources():
    package = Path(__file__).parent
    installed = package / "resources"
    if (installed / "skills" / "factory" / "SKILL.md").is_file():
        return installed
    repo = package.parent / ".claude"
    if (repo / "skills" / "factory" / "SKILL.md").is_file():
        return repo
    raise FactoryError("No se encontraron la skill y los agentes para instalar.")


def install_global():
    """Copia skill y agentes a ~/.claude; no sobrescribe settings existentes."""
    source = _resources()
    root = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    skills = root / "skills" / "factory"
    agents = root / "agents"
    skills.parent.mkdir(parents=True, exist_ok=True)
    agents.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source / "skills" / "factory", skills, dirs_exist_ok=True)
    count = 0
    for agent in sorted((source / "agents").glob("devforge-*.md")):
        shutil.copy2(agent, agents / agent.name)
        count += 1
    if not count:
        raise FactoryError("No hay agentes devforge-*.md para instalar.")
    settings = source / "settings.json"
    target = root / "settings.json"
    if target.exists():
        note = "existe; combínalo a mano con el de referencia"
    else:
        shutil.copy2(settings, target)
        note = "copiado"
    return f"Skill: {skills}\nAgentes: {count} en {agents}\nSettings: {target} ({note})"
