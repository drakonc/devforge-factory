"""Instalación de la skill y los agentes en la configuración del usuario."""

import json
import os
import shutil
from pathlib import Path


def _resources():
    # Import diferido: el script bash usa _merge_settings con un python3 que puede no tener PyYAML.
    from .core import FactoryError

    package = Path(__file__).parent
    installed = package / "resources"
    if (installed / "skills" / "factory" / "SKILL.md").is_file():
        return installed
    repo = package.parent / ".claude"
    if (repo / "skills" / "factory" / "SKILL.md").is_file():
        return repo
    raise FactoryError("No se encontraron la skill y los agentes para instalar.")


def _identity(item):
    """Clave para comparar elementos de listas; las entradas con name/path se comparan por ese campo."""
    if isinstance(item, dict) and ("name" in item or "path" in item):
        item = item.get("name", item.get("path"))
    return json.dumps(item, sort_keys=True)


def _merge(current, reference, path, added, kept):
    """Añade lo que falta de reference en current; nunca reemplaza valores existentes."""
    for key, value in reference.items():
        here = f"{path}.{key}" if path else key
        if key not in current:
            current[key] = value
            added.append(here)
        elif isinstance(current[key], dict) and isinstance(value, dict):
            _merge(current[key], value, here, added, kept)
        elif isinstance(current[key], list) and isinstance(value, list):
            seen = {_identity(item) for item in current[key]}
            missing = [item for item in value if _identity(item) not in seen]
            if missing:
                current[key].extend(missing)
                added.append(here)
        elif current[key] != value:
            kept.append(here)


def _merge_settings(reference, target):
    """Combina la plantilla en settings existentes conservando todo lo que el usuario ya tiene."""
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = None
    if not isinstance(data, dict):
        return f"existe pero no es un objeto JSON legible; combínalo a mano con {reference}"
    added, kept = [], []
    _merge(data, json.loads(reference.read_text(encoding="utf-8")), "", added, kept)
    if not added:
        note = "existe; ya contiene la configuración de referencia"
    else:
        # Respaldo y reemplazo atómico sobre el destino real (respeta symlinks de dotfiles).
        real = target.resolve()
        backup = real.with_name(real.name + ".bak")
        shutil.copy2(real, backup)
        temp = real.with_name(real.name + ".tmp")
        temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        shutil.copymode(real, temp)
        os.replace(temp, real)
        note = f"existe; añadido: {', '.join(added)}; respaldo en {backup}"
    if kept:
        note += f"; se conservan tus valores en: {', '.join(kept)}"
    return note


def install_global():
    """Copia skill y agentes a ~/.claude; en settings existentes solo añade lo que falta."""
    from .core import FactoryError

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
        note = _merge_settings(settings, target)
    else:
        shutil.copy2(settings, target)
        note = "copiado"
    return f"Skill: {skills}\nAgentes: {count} en {agents}\nSettings: {target} ({note})"
