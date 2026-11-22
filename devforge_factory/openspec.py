"""Adaptador para importar un cambio de OpenSpec como trabajo local."""

import os
import re
import shutil
import subprocess
from pathlib import Path

from .core import FactoryError, create_job, git, now, project_root, write_job

REQUIRED = ("proposal.md", "design.md", "tasks.md")
MAX_TOTAL_BYTES = 5 * 1024 * 1024


def _read_artifact(path):
    if path.is_symlink() or not path.is_file():
        raise FactoryError(f"El cambio OpenSpec no contiene {path.name} legible.")
    if path.stat().st_size > MAX_TOTAL_BYTES:
        raise FactoryError(f"El artefacto {path.name} supera 5 MiB.")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FactoryError(f"No se pudo leer {path.name}: {exc}") from exc


def _spec_files(folder):
    base = folder / "specs"
    if base.is_symlink() or not base.is_dir():
        return []
    found = []
    for directory, folders, files in os.walk(base, followlinks=False):
        folders[:] = [name for name in folders if not (Path(directory) / name).is_symlink()]
        for name in files:
            item = Path(directory) / name
            if name == "spec.md" and not item.is_symlink() and item.is_file():
                found.append(item)
    return sorted(found)


def _title(proposal, change_id):
    for line in proposal.splitlines():
        if line.startswith("# ") and line[2:].strip():
            return line[2:].strip()
    for line in proposal.splitlines():
        value = line.strip()
        if not value or value.startswith(("#", ">", "|", "```")):
            continue
        value = value.lstrip("-* ").strip()
        if value and not value.endswith(":"):
            return value[:120]
    return change_id.replace("-", " ")


def _combined(change_id, artifacts, specs):
    parts = [f"Cambio OpenSpec: {change_id}", f"Ruta: openspec/changes/{change_id}"]
    for name in REQUIRED:
        parts.append(f"## {name}\n\n{artifacts[name].strip()}")
    for path, content in specs:
        parts.append(f"## {path}\n\n{content.strip()}")
    return "\n\n".join(parts) + "\n"


def import_change(cwd, change_id, branch_type="feature"):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", change_id):
        raise FactoryError("Identificador de cambio OpenSpec inválido.")
    root = project_root(cwd)
    for name in ("openspec", "changes"):
        if (root / name).is_symlink():
            raise FactoryError("La ruta del cambio OpenSpec no puede atravesar enlaces simbólicos.")
    folder = root / "openspec" / "changes" / change_id
    if folder.is_symlink() or not folder.is_dir():
        raise FactoryError(f"No existe el cambio OpenSpec {change_id} o es un enlace simbólico.")
    artifacts = {name: _read_artifact(folder / name) for name in REQUIRED}
    specs = []
    total = sum(len(content.encode("utf-8")) for content in artifacts.values())
    if total > MAX_TOTAL_BYTES:
        raise FactoryError("El cambio OpenSpec supera el límite de 5 MiB.")
    for path in _spec_files(folder):
        content = _read_artifact(path)
        total += len(content.encode("utf-8"))
        if total > MAX_TOTAL_BYTES:
            raise FactoryError("El cambio OpenSpec supera el límite de 5 MiB.")
        specs.append((path.relative_to(folder).as_posix(), content))
    if not specs:
        raise FactoryError("El cambio OpenSpec no contiene specs/**/spec.md.")
    staging = root / ".devforge" / "import-staging"
    if staging.is_symlink():
        raise FactoryError("La carpeta de importación no puede ser un enlace simbólico.")
    staging.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = staging / f"openspec-{change_id}.md"
    if target.is_symlink():
        raise FactoryError("La ruta de importación no puede ser un enlace simbólico.")
    title = _title(artifacts["proposal.md"], change_id)
    combined = _combined(change_id, artifacts, specs)
    target.write_text(combined, encoding="utf-8")
    job = create_job(
        cwd, "openspec", combined, change_id,
        document=f"openspec/changes/{change_id}", branch_type=branch_type, title=title,
    )
    target.unlink(missing_ok=True)
    return job


def _run(binary, args, root):
    try:
        result = subprocess.run([binary, *args], cwd=root, text=True, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FactoryError(f"No se pudo ejecutar openspec {' '.join(args)}: {exc}") from exc
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise FactoryError(f"openspec {' '.join(args)} falló: {detail}")


def archive_job(root, folder, job):
    """Valida, sincroniza y archiva el cambio OpenSpec de un trabajo aprobado."""
    if job.get("source") != "openspec":
        return ""
    change_id = str(job.get("key") or "")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", change_id):
        raise FactoryError("El trabajo no conserva un identificador OpenSpec válido.")
    binary = shutil.which("openspec")
    if not binary:
        raise FactoryError("El trabajo proviene de OpenSpec y el CLI `openspec` no está disponible.")
    base = str(job.get("base_branch", "develop"))
    sha = str(job.get("reviewed_sha") or "")
    integrated = bool(sha) and git(root, "merge-base", "--is-ancestor", sha, base, check=False).returncode == 0
    _run(binary, ["validate", "--strict", change_id], root)
    _run(binary, ["archive", "--yes", change_id], root)
    job["openspec_archived"] = True
    job["openspec_archived_at"] = now()
    job["openspec_integrated"] = integrated
    write_job(folder, job)
    message = f"OpenSpec {change_id}: validado, sincronizado y archivado."
    if not integrated:
        message += f" Aviso: {sha[:12] or 'sin SHA'} no está en {base}; se archivó tras la confirmación humana."
    return message
