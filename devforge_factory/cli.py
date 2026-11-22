"""Interfaz de línea de comandos para /factory."""

from __future__ import annotations

import argparse
import os
import sys
from . import lifecycle
import subprocess
from pathlib import Path

from . import __version__
from .core import FactoryError, document_paths, repository_slug, config_for, create_job, extract_file, jobs, project_root, publish_draft_pr, read_job, transition


MENU = [("hacer", "Crear un trabajo"), ("plan", "Planificar un trabajo"), ("seguir", "Reanudar un trabajo"), ("ver", "Ver trabajos"), ("revisar", "Ejecutar Quality Gates"), ("parar", "Pausar un trabajo")]


def select_job(path: Path, job_id: str | None):
    all_jobs = jobs(path)
    if job_id:
        match = [(folder, job) for folder, job in all_jobs if job["id"] == job_id]
        if not match:
            raise FactoryError(f"No existe el trabajo {job_id}.")
        return match[0]
    if not all_jobs:
        raise FactoryError("No hay trabajos. Usa `devforge hacer <solicitud>`.")
    print("Trabajos disponibles:")
    for index, (_, job) in enumerate(all_jobs, 1):
        print(f"{index}. {job['id']} [{job['status']}] {job['title']}")
    try:
        selected = int(input("Selecciona: ")) - 1
        return all_jobs[selected]
    except (ValueError, IndexError) as exc:
        raise FactoryError("Selección inválida.") from exc


def create_from(args) -> None:
    source = getattr(args, "source", None)
    key = getattr(args, "key", "") or ""
    staged_import = False
    if args.file:
        raw_file_path = Path(args.file).expanduser()
        file_path = raw_file_path.resolve()
        if source in {"email", "github", "jira", "azure", "openspec"}:
            root, _ = config_for(Path.cwd())
            staging_path = root / ".devforge" / "import-staging"
            staging = staging_path.resolve()
            if (file_path.parent == staging and raw_file_path.absolute().parent == staging_path.absolute()
                    and not staging_path.is_symlink() and not raw_file_path.is_symlink()):
                staged_import = True
            else:
                raise FactoryError("Las importaciones conectadas deben guardarse temporalmente en .devforge/import-staging/.")
        elif source not in (None, "file"):
            raise FactoryError("Origen de archivo inválido.")
        text = extract_file(file_path)
    elif args.url:
        raise FactoryError("DevForge no consulta servicios remotos ni tokens. Usa las integraciones conectadas de Claude y pasa el contenido mediante un archivo temporal de staging.")
    else:
        if getattr(args, "stdin", False):
            if args.request:
                raise FactoryError("No combines una solicitud posicional con --stdin.")
            text = sys.stdin.read()
        else:
            text = args.request or input("Describe la solicitud: ").strip()
        if source == "file":
            raise FactoryError("El origen file requiere --file.")
        source = source or "direct"
    if not text.strip():
        raise FactoryError("La solicitud está vacía.")
    if source is None:
        source = "file" if args.file else "direct"
    options = {}
    if getattr(args, "branch_type", "feature") != "feature":
        options["branch_type"] = args.branch_type
    if source == "file":
        root = project_root(Path.cwd())
        document = str(file_path.relative_to(root)) if file_path.is_relative_to(root) else file_path.name
        options["document"] = document
    folder = create_job(Path.cwd(), source, text, key, **options)
    if staged_import:
        file_path.unlink(missing_ok=True)
    print(f"Trabajo creado: {folder.name}")
    print(f"Estado: queued | Revisa y planifica con `devforge plan {folder.name}`")


def list_jobs(path: Path) -> None:
    found = jobs(path)
    if not found:
        print("No hay trabajos.")
        return
    for _, job in found:
        print(f"{job['id']} [{job['status']}] {job['title']} — rama {job['branch']}")


def handle(action: str, job_id: str | None, args) -> None:
    cwd = Path.cwd()
    if action == "hacer":
        create_from(args)
        return
    if action == "ver":
        list_jobs(cwd)
        return
    folder, _ = select_job(cwd, job_id)
    with lifecycle.job_lock(folder):
        handle_job(action, folder, read_job(folder), cwd)


def handle_job(action, folder, job, cwd):
    if action == "plan":
        if job["status"] not in {"queued", "planned"}:
            raise FactoryError(f"El trabajo está en estado {job['status']} y no se puede planificar.")
        transition(folder, "planned")
        print(f"Plan pendiente para Claude Code: {folder / 'plan.md'}")
        print(f"Worktree: {job['worktree']} | rama: {job['branch']}")
        return
    if action == "seguir":
        print(lifecycle.resume(folder, job))
        return
    if action == "parar":
        print(lifecycle.pause(folder, job))
        return
    if action == "revisar":
        print(lifecycle.review(folder, job, cwd))
        return
    if action == "rework":
        print(lifecycle.rework(folder, job))
        return
    if action == "cerrar":
        print(lifecycle.close(folder, job))
        return
    if action == "publicar":
        lifecycle.acceptance(folder, job)
        print(f"PR borrador creada: {publish_draft_pr(folder)}")
        return
    raise FactoryError(f"Acción desconocida: {action}")


def interactive() -> None:
    print("DevForge Factory")
    for number, (action, description) in enumerate(MENU, 1):
        print(f"{number}. {action} — {description}")
    try:
        selected = input("Acción: ").strip().lower()
        if selected.isdigit():
            selected = MENU[int(selected) - 1][0]
    except (ValueError, IndexError) as exc:
        raise FactoryError("Selección inválida.") from exc
    if selected == "hacer":
        class NewArgs:
            file = None
            url = None
            request = None
            stdin = False
            source = None
            key = ""
        create_from(NewArgs())
    elif selected in {"plan", "seguir", "ver", "revisar", "parar"}:
        handle(selected, None, None)
    else:
        raise FactoryError(f"Acción desconocida: {selected}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="devforge", description="DevForge Factory — fábrica local de software")
    result.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = result.add_subparsers(dest="action")
    sub.add_parser("init", help="Prepara la fábrica en el proyecto actual")
    sub.add_parser("instalar-global", help="Instala la skill y los agentes en la configuración del usuario")
    sub.add_parser("repo", help="Identifica el repositorio asociado a origin")
    sub.add_parser("documentos", help="Lista documentos candidatos bajo docs/")
    openspec = sub.add_parser("openspec", help="Importa un cambio de OpenSpec como trabajo")
    openspec.add_argument("change_id")
    openspec.add_argument("--type", dest="branch_type", choices=("feature", "fix", "hotfix", "chore"), default="feature")
    create = sub.add_parser("hacer", help="Crea un trabajo desde texto, archivo o contenido importado por Claude")
    create.add_argument("request", nargs="?")
    source = create.add_mutually_exclusive_group()
    source.add_argument("--file")
    source.add_argument("--url", help="No consulta servicios; use una integración Claude y pase el contenido por stdin")
    source.add_argument("--stdin", action="store_true", help="Lee por stdin el contenido obtenido por una integración conectada")
    create.add_argument("--source", choices=("direct", "email", "jira", "github", "azure", "file"))
    create.add_argument("--key", help="Identificador de la solicitud en el sistema de origen")
    create.add_argument("--type", dest="branch_type", choices=("feature", "fix", "hotfix", "chore"), default="feature")
    sub.add_parser("cola", help="Lista trabajos de la cola local")
    sub.add_parser("tomar", help="Reserva un trabajo o el próximo disponible").add_argument("job_id", nargs="?")
    sub.add_parser("liberar", help="Libera una reserva").add_argument("job_id")
    sub.add_parser("dashboard", help="Genera un tablero HTML local")
    for action in ("plan", "seguir", "ver", "revisar", "parar", "publicar", "rework", "cerrar"):
        command = sub.add_parser(action)
        command.add_argument("job_id", nargs="?")
    sub.add_parser("herd-status", help="Muestra si hay una sesión Herdr invocable")
    return result


def main() -> None:
    try:
        args = parser().parse_args()
        if not args.action:
            interactive()
        elif args.action == "init":
            from .core import init_project

            init_project(Path.cwd())
        elif args.action in {"cola", "dashboard", "tomar", "liberar"}:
            from . import board
            if args.action == "cola":
                board.show_queue(Path.cwd())
            elif args.action == "dashboard":
                print(board.dashboard(Path.cwd()))
            elif args.action == "tomar":
                print(board.claim_next(Path.cwd(), args.job_id))
            else:
                board.release(Path.cwd(), args.job_id)
        elif args.action == "instalar-global":
            from .install import install_global

            print(install_global())
        elif args.action == "openspec":
            from .openspec import import_change

            folder = import_change(Path.cwd(), args.change_id, args.branch_type)
            print(f"Trabajo creado: {folder.name}")
            print(f"Estado: queued | Revisa y planifica con `devforge plan {folder.name}`")
        elif args.action == "repo":
            print(repository_slug(Path.cwd()))
        elif args.action == "documentos":
            print("\n".join(document_paths(Path.cwd())) or "No hay documentos candidatos en docs/.")
        elif args.action == "herd-status":
            terminal = os.getenv("HC_TERMINAL_ID")
            hc = shutil_which("hc")
            active = False
            if terminal and hc:
                probe = subprocess.run([hc, "get", terminal, "--json"], text=True, capture_output=True)
                active = probe.returncode == 0
            if active:
                opencode = shutil_which("opencode")
                codex = shutil_which("codex")
                print(f"Sesión Herdr verificada: {terminal}")
                print(f"OpenCode: {'disponible' if opencode else 'no instalado'}; Codex: {'disponible' if codex else 'no instalado'}.")
                if not opencode or not codex:
                    print("Se usarán subagentes Claude Code para las herramientas faltantes.")
            else:
                print("Sesión Herdr no verificada; se usarán subagentes Claude Code.")
        else:
            handle(args.action, getattr(args, "job_id", None), args)
    except FactoryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def shutil_which(name: str) -> str | None:
    import shutil

    return shutil.which(name)


if __name__ == "__main__":
    main()

