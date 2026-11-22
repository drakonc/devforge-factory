"""Estado local, ingesta y operaciones seguras de la fábrica."""

from __future__ import annotations

import json
import os
import re
import selectors
import shutil
import subprocess
import time
import urllib.parse
import unicodedata
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import yaml


class FactoryError(RuntimeError):
    """Error esperado que puede mostrarse directamente al usuario."""


STATES = {"queued", "planned", "working", "review", "paused", "done", "blocked"}
TRANSITIONS = {
    "queued": {"planned", "paused", "blocked"},
    "planned": {"working", "paused", "blocked"},
    "working": {"review", "paused", "blocked"},
    "review": {"working", "done", "paused", "blocked"},
    "paused": {"queued", "planned", "working", "review", "blocked"},
    "blocked": {"queued", "planned", "working", "review", "paused"},
    "done": set(),
}
SUPPORTED_GATES = {"git-diff-check", "tests-configured", "human-approval"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = "".join(character for character in unicodedata.normalize("NFKD", value) if not unicodedata.combining(character))
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return (value or "solicitud")[:48].rstrip("-")


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if check and result.returncode:
        raise FactoryError(result.stderr.strip() or f"Falló git {' '.join(args)}")
    return result


def load_yaml(path: Path) -> dict:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FactoryError(f"No se pudo leer la configuración {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FactoryError(f"La configuración {path} debe contener un objeto YAML.")
    return value


def project_root(path: Path) -> Path:
    path = path.resolve()
    root = git(path, "rev-parse", "--show-toplevel", check=False)
    return Path(root.stdout.strip()).resolve() if root.returncode == 0 else path


def azure_repository(remote: str) -> str | None:
    """Identifica las URLs modernas de Azure DevOps Services sin usar la red."""
    https = re.fullmatch(r"https://(?:([A-Za-z0-9-]+)@)?dev\.azure\.com/([^/]+)/([^/]+)/_git/([^/]+)/?", remote, re.I)
    ssh = re.fullmatch(r"(?:git@ssh\.dev\.azure\.com:|ssh://git@ssh\.dev\.azure\.com/)v3/([^/]+)/([^/]+)/([^/]+)/?", remote, re.I)
    if https:
        username, org, project, repo = https.groups()
        if username and username.lower() != org.lower():
            raise FactoryError("El usuario del remoto Azure no coincide con su organización.")
    elif ssh:
        org, project, repo = ssh.groups()
    else:
        return None
    if not re.fullmatch(r"[A-Za-z0-9-]+", org):
        raise FactoryError("Organización de Azure inválida.")
    names = []
    for part in (project, repo):
        name = urllib.parse.unquote(part)
        if not name.strip() or name in {".", ".."} or any(c in "/\\?#%@" or not c.isprintable() for c in name):
            raise FactoryError("El proyecto o repositorio de Azure contiene caracteres no admitidos.")
        names.append(urllib.parse.quote(name, safe=""))
    return f"https://dev.azure.com/{org}/{names[0]}/_git/{names[1]}"


def repository_slug(path: Path) -> str:
    result = git(path, "remote", "get-url", "origin", check=False)
    if result.returncode:
        raise FactoryError("No hay origin para identificar el repositorio actual.")
    remote = result.stdout.strip()
    azure = azure_repository(remote)
    if azure:
        return azure
    _, slug = _remote_identity(remote)
    if slug.count("/") != 1:
        raise FactoryError("El origin no identifica un repositorio compatible de GitHub o Azure Repos.")
    return slug


def document_paths(path: Path) -> list[str]:
    root = project_root(path)
    docs = root / "docs"
    if docs.is_symlink() or not docs.is_dir():
        return []
    candidates = []
    for directory, folders, files in os.walk(docs, followlinks=False):
        folders[:] = [name for name in folders if not name.startswith(".") and name != "requerimientio"]
        for name in files:
            item = Path(directory) / name
            if not item.is_symlink() and item.is_file() and item.suffix.lower() in {".md", ".markdown", ".txt", ".pdf", ".docx"}:
                candidates.append(item.relative_to(root).as_posix())
    return sorted(candidates)


def config_for(path: Path) -> tuple[Path, dict]:
    root = project_root(path)
    config_dir = root / ".devforge"
    if config_dir.is_symlink():
        raise FactoryError("La carpeta .devforge no puede ser un enlace simbólico.")
    config = config_dir / "project.yaml"
    if not config.is_file():
        raise FactoryError(f"No existe {config}. Ejecuta `devforge init`.")
    if config.is_symlink():
        raise FactoryError("La configuración .devforge/project.yaml no puede ser un enlace simbólico.")
    return root, load_yaml(config)


def ensure_within(parent: Path, child: Path) -> Path:
    resolved = child.resolve()
    if not resolved.is_relative_to(parent.resolve()):
        raise FactoryError("La ruta calculada sale del directorio de worktrees permitido.")
    return resolved


def extract_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if path.stat().st_size > 20 * 1024 * 1024:
        raise FactoryError("El archivo supera el límite de 20 MiB.")
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".pdf":
        binary = shutil.which("pdftotext")
        if not binary:
            raise FactoryError("Para leer PDF instala poppler-utils (comando pdftotext).")
        process = subprocess.Popen([binary, "-layout", str(path), "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        chunks: list[bytes] = []
        total = 0
        deadline = time.monotonic() + 45
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FactoryError("La extracción del PDF excedió 45 segundos.")
                events = selector.select(min(remaining, 0.25))
                if events:
                    chunk = os.read(process.stdout.fileno(), 64 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 10 * 1024 * 1024:
                        raise FactoryError("El texto extraído supera el límite de 10 MiB.")
                    chunks.append(chunk)
                elif process.poll() is not None:
                    break
            return_code = process.wait(timeout=max(0.1, deadline - time.monotonic()))
            if return_code:
                raise FactoryError("No se pudo extraer el PDF con pdftotext.")
            return b"".join(chunks).decode("utf-8", errors="replace")
        finally:
            selector.close()
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(path) as docx:
                info = docx.getinfo("word/document.xml")
                if info.file_size > 50 * 1024 * 1024:
                    raise FactoryError("El contenido DOCX supera el límite de 50 MiB descomprimido.")
                xml = ElementTree.fromstring(docx.read(info))
        except (OSError, zipfile.BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise FactoryError(f"No se pudo leer el DOCX: {exc}") from exc
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        return "\n".join("".join(node.itertext()) for node in xml.findall(".//w:p", ns))
    raise FactoryError("Formato no admitido; usa Markdown, TXT, PDF o DOCX.")


def normalize(source: str, text: str, key: str = "") -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = (lines[0].lstrip("# ").strip() if lines else "Solicitud DevForge")[:180]
    return {
        "source": source,
        "key": key,
        "title": title,
        "description": text.strip(),
        "acceptance_criteria": [],
        "created_at": now(),
    }


def read_job(job_path: Path) -> dict:
    try:
        job = json.loads((job_path / "job.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FactoryError(f"No se pudo leer el trabajo {job_path.name}: {exc}") from exc
    if job.get("status") not in STATES:
        raise FactoryError(f"Estado inválido en {job_path.name}.")
    return job


def write_job(job_path: Path, job: dict) -> None:
    job["updated_at"] = now()
    temp = job_path / ".job.json.tmp"
    temp.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(job_path / "job.json")


def transition(job_path: Path, status: str) -> dict:
    if status not in STATES:
        raise FactoryError(f"Estado desconocido: {status}")
    job = read_job(job_path)
    if status != job["status"] and status not in TRANSITIONS[job["status"]]:
        raise FactoryError(f"Transición no permitida: {job['status']} → {status}")
    job["status"] = status
    write_job(job_path, job)
    return job


def init_project(path: Path) -> None:
    root = Path(git(path, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    config_dir = root / ".devforge"
    if config_dir.is_symlink():
        raise FactoryError("La carpeta .devforge no puede ser un enlace simbólico.")
    gitignore = root / ".gitignore"
    if gitignore.is_symlink():
        raise FactoryError(".gitignore no puede ser un enlace simbólico.")
    config_dir.mkdir(exist_ok=True)
    target = config_dir / "project.yaml"
    if target.exists() or target.is_symlink():
        raise FactoryError(f"No se sobrescribe configuración existente: {target}")
    defaults = load_yaml(Path(__file__).with_name("defaults.yaml"))
    if git(root, "show-ref", "--verify", "--quiet", "refs/heads/develop", check=False).returncode:
        remote_head = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False)
        branch = remote_head.stdout.strip().removeprefix("origin/")
        if not branch or git(root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode:
            branch = git(root, "symbolic-ref", "--short", "HEAD", check=False).stdout.strip()
        if branch:
            defaults["base_branch"] = branch
    target.write_text(
        yaml.safe_dump(defaults, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    (config_dir / "import-staging").mkdir(mode=0o700, exist_ok=True)
    content = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    missing = [entry for entry in (".devforge/jobs/", ".devforge/worktrees/", ".devforge/import-staging/") if entry not in content.splitlines()]
    if missing:
        gitignore.write_text(content + ("\n" if content and not content.endswith("\n") else "") + "".join(f"{entry}\n" for entry in missing), encoding="utf-8")
    print(f"Configuración creada: {target}")


def create_job(path: Path, source: str, text: str, key: str = "", *, document: str = "", branch_type: str = "feature", title: str = "") -> Path:
    root, config = config_for(path)
    if source not in {"direct", "email", "jira", "github", "azure", "openspec", "file"}:
        raise FactoryError("Origen inválido; usa direct, email, jira, github, azure, openspec o file.")
    max_rounds = config.get("max_rounds", 3)
    if type(max_rounds) is not int or max_rounds < 1:
        raise FactoryError("max_rounds debe ser un entero positivo.")
    configured_worktrees = root / config.get("worktree_dir", ".devforge/worktrees")
    cursor = root
    for part in Path(config.get("worktree_dir", ".devforge/worktrees")).parts:
        if part in {"", "."}:
            continue
        cursor = cursor / part
        if cursor.is_symlink():
            raise FactoryError("worktree_dir no puede atravesar enlaces simbólicos.")
    worktrees = configured_worktrees.resolve()
    if not worktrees.is_relative_to(root):
        raise FactoryError("worktree_dir debe quedar dentro del repositorio para respetar el aislamiento del proyecto.")
    worktrees.mkdir(parents=True, exist_ok=True)
    normalized = normalize(source, text, key)
    if title:
        normalized["title"] = title[:180]
    job_key = key or f"DF-{uuid.uuid4().hex[:8].upper()}"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", job_key):
        raise FactoryError("El identificador de origen solo puede usar letras, números, punto, guion y guion bajo.")
    job_key_slug = slugify(job_key)
    job_id = f"{job_key_slug}-{slugify(normalized['title'])}"
    job_path = root / ".devforge" / "jobs" / job_id
    if job_path.parent.is_symlink():
        raise FactoryError("La carpeta .devforge/jobs no puede ser un enlace simbólico.")
    if job_path.exists():
        raise FactoryError(f"Ya existe el trabajo {job_id}.")
    if branch_type not in {"feature", "fix", "hotfix", "chore"}:
        raise FactoryError("Tipo de rama inválido.")
    branch = f"{branch_type}/{job_key_slug}-{slugify(normalized['title'])}"
    base = str(config.get("base_branch", "develop"))
    base_check = git(root, "show-ref", "--verify", f"refs/heads/{base}", check=False)
    if base_check.returncode:
        raise FactoryError(f"La rama base local `{base}` no existe. Configura base_branch en .devforge/project.yaml.")
    worktree_path = ensure_within(worktrees, worktrees / job_id)
    if worktree_path.exists():
        raise FactoryError(f"Ya existe la ruta de worktree {worktree_path}.")
    branch_check = git(root, "show-ref", "--verify", f"refs/heads/{branch}", check=False)
    if branch_check.returncode == 0:
        raise FactoryError(f"Ya existe la rama {branch}; no se reutiliza automáticamente.")
    job_path.mkdir(mode=0o700, parents=True)
    branch_created = False
    try:
        (job_path / "request.md").write_text(f"# {normalized['title']}\n\n{normalized['description']}\n", encoding="utf-8")
        (job_path / "plan.md").write_text(f"# Plan de trabajo: {normalized['title']}\n\nEstado: pendiente de planificación por Claude Code.\n\n## Criterios de aceptación\n\nPendiente de extraer de la solicitud.\n", encoding="utf-8")
        created_branch = git(root, "branch", branch, base, check=False)
        if created_branch.returncode:
            raise FactoryError(created_branch.stderr.strip())
        branch_created = True
        add = git(root, "worktree", "add", str(worktree_path), branch, check=False)
        if add.returncode:
            raise FactoryError(add.stderr.strip())
    except Exception:
        worktree_list = git(root, "worktree", "list", "--porcelain", check=False).stdout
        if f"worktree {worktree_path}\n" in worktree_list:
            git(root, "worktree", "remove", "--force", str(worktree_path), check=False)
        if branch_created:
            git(root, "branch", "-D", branch, check=False)
        shutil.rmtree(job_path)
        raise
    job = {
        "id": job_id,
        "key": job_key,
        "title": normalized["title"],
        "source": source,
        **({"document": document} if document else {}),
        "description": normalized["description"],
        "status": "queued",
        "round": 1,
        "max_rounds": max_rounds,
        "branch": branch,
        "base_branch": base,
        "worktree": str(worktree_path),
        "created_at": now(),
        "updated_at": now(),
        "human_approval_required": True,
        "pull_request": None,
        "quality_gates": config.get("quality_gates", []),
        "test_command": config.get("test_command", []),
        "test_env": config.get("test_env", []),
    }
    try:
        write_job(job_path, job)
    except Exception:
        git(root, "worktree", "remove", "--force", str(worktree_path), check=False)
        git(root, "branch", "-D", branch, check=False)
        shutil.rmtree(job_path)
        raise
    return job_path


def jobs(path: Path) -> list[tuple[Path, dict]]:
    root = project_root(path)
    folder = root / ".devforge" / "jobs"
    if not folder.exists():
        return []
    result = []
    for job_file in sorted(folder.glob("*/job.json")):
        job_path = job_file.parent
        result.append((job_path, read_job(job_path)))
    return result


def run_gate(path: Path, job: dict) -> tuple[bool, str]:
    root, config = config_for(path)
    worktree = Path(job["worktree"]).resolve()
    if not worktree.is_dir():
        return False, "El worktree configurado ya no existe."
    allowed_worktrees = (root / config.get("worktree_dir", ".devforge/worktrees")).resolve()
    if not worktree.is_relative_to(allowed_worktrees):
        return False, "El worktree configurado sale de la ruta permitida del proyecto."
    gates = job.get("quality_gates", [])
    if not isinstance(gates, list) or set(gates) - SUPPORTED_GATES:
        return False, "quality_gates contiene nombres no soportados; configura solo git-diff-check, tests-configured y human-approval."
    status = git(worktree, "status", "--porcelain", "--untracked-files=all", check=False)
    if status.returncode or status.stdout.strip():
        return False, "working-tree: FAIL; confirma que el trabajo está committeado y limpio antes de revisar."
    diff = git(worktree, "diff", "--check", f"{job['base_branch']}...HEAD", check=False)
    if diff.returncode:
        return False, "git diff --check: FAIL"
    report = ["working-tree: PASS", "git diff --check: PASS"]
    test_command = job.get("test_command") or []
    if "tests-configured" in job.get("quality_gates", []):
        if not isinstance(test_command, list) or not test_command or not all(isinstance(arg, str) for arg in test_command):
            return False, "tests-configured: FAIL; configura test_command como una lista de argumentos en .devforge/project.yaml"
        allowed_names = job.get("test_env", [])
        if not isinstance(allowed_names, list) or not all(isinstance(name, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) for name in allowed_names):
            return False, "test_env: FAIL; debe ser una lista de nombres de variables válidos."
        bwrap = shutil.which("bwrap")
        if not bwrap:
            return False, "test-command: FAIL (bwrap no está instalado; ejecución aislada obligatoria)"
        safe_env = {name: os.environ[name] for name in ("LANG", "LC_ALL", "LC_CTYPE", "TZ") if name in os.environ}
        try:
            safe_env.update({name: os.environ[name] for name in allowed_names if name in os.environ})
            sandbox_command = [
                bwrap, "--unshare-all", "--die-with-parent", "--ro-bind", "/usr", "/usr",
                "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
                "--tmpfs", "/etc", "--dir", "/etc", "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
                "--dir", "/mnt", "--bind", str(worktree), "/mnt", "--tmpfs", "/home", "--tmpfs", "/root",
                "--tmpfs", "/run", "--tmpfs", "/tmp", "--dir", "/tmp/home",
                "--proc", "/proc", "--dev", "/dev", "--chdir", "/mnt", "--clearenv",
                "--setenv", "HOME", "/tmp/home", "--setenv", "TMPDIR", "/tmp",
                "--setenv", "PATH", "/usr/local/bin:/usr/bin",
            ]
            for name, value in safe_env.items():
                sandbox_command.extend(("--setenv", name, value))
            sandbox_command.extend(("--", *test_command))
            test = subprocess.run(sandbox_command, cwd=worktree, env={}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
        except subprocess.TimeoutExpired:
            return False, "test-command: FAIL (excedió el límite de 30 minutos)"
        except OSError:
            return False, "test-command: FAIL (no se pudo iniciar el comando configurado)"
        report.append(f"test-command: {'PASS' if test.returncode == 0 else 'FAIL'} (exit code {test.returncode})")
        if test.returncode:
            return False, "\n".join(report)
        final_status = git(worktree, "status", "--porcelain", "--untracked-files=all", check=False)
        if final_status.returncode or final_status.stdout.strip():
            return False, "test-command: FAIL (el comando modificó el worktree; restáuralo y vuelve a ejecutar gates)"
    if "human-approval" in job.get("quality_gates", []):
        report.append("human-approval: PENDING (requerida antes de publicar PR o completar)")
    return True, "\n".join(report)


def publish_draft_pr(job_path: Path) -> str:
    """Publica una rama y abre un PR borrador tras aprobación exacta en terminal."""
    job = read_job(job_path)
    if job["status"] != "review":
        raise FactoryError("Solo se puede publicar un trabajo con Quality Gates aprobados y en revisión.")
    if job.get("pull_request_head_mismatch"):
        raise FactoryError("La PR borrador anterior tiene un SHA distinto del revisado; el trabajo requiere intervención humana.")
    gate_report = job_path / "quality-gates.md"
    if not gate_report.is_file():
        raise FactoryError("Falta el informe aprobado de Quality Gates.")
    gate_text = gate_report.read_text(encoding="utf-8")
    gates = job.get("quality_gates", [])
    if not isinstance(gates, list) or set(gates) - SUPPORTED_GATES:
        raise FactoryError("Hay Quality Gates no soportados; no se publica.")
    required_results = []
    if "git-diff-check" in gates:
        required_results.append("git diff --check: PASS")
    required_results.append("working-tree: PASS")
    if "tests-configured" in gates:
        required_results.append("test-command: PASS")
    if "human-approval" in gates:
        required_results.append("human-approval: PENDING")
    if any(result not in gate_text for result in required_results) or any("FAIL" in line for line in gate_text.splitlines()):
        raise FactoryError("Los Quality Gates no están todos aprobados o requieren configuración.")
    for report_name in ("review-code.md", "review-security.md", "review-qa.md"):
        report = job_path / report_name
        if not report.is_file():
            raise FactoryError(f"Falta la revisión obligatoria: {report_name}.")
        verdict = report.read_text(encoding="utf-8").strip().upper()
        if (not verdict.startswith("APTO") or "NO APTO" in verdict or "BLOQUEADO" in verdict
                or f"HEAD: {str(job.get('reviewed_sha', '')).upper()}" not in verdict):
            raise FactoryError(f"La revisión {report_name} no aprobó la publicación.")
    branch = git(Path(job["worktree"]), "branch", "--show-current").stdout.strip()
    if branch != job["branch"]:
        raise FactoryError("La rama activa no coincide con la rama persistida del trabajo.")
    worktree = Path(job["worktree"])
    head = git(worktree, "rev-parse", "HEAD").stdout.strip()
    if not job.get("reviewed_sha") or head != job["reviewed_sha"]:
        raise FactoryError("HEAD cambió desde la revisión. Repite gates, revisiones y aprobación.")
    if git(worktree, "status", "--porcelain", "--untracked-files=all").stdout.strip():
        raise FactoryError("El worktree tiene cambios sin revisar. Repite gates y revisiones.")
    commits = git(worktree, "rev-list", "--count", f"{job['base_branch']}..{branch}").stdout.strip()
    if not commits.isdigit() or int(commits) < 1:
        raise FactoryError("No hay commits nuevos para publicar.")
    remote_result = git(worktree, "remote", "get-url", "origin", check=False)
    if remote_result.returncode or not remote_result.stdout.strip():
        raise FactoryError("No hay un remote origin configurado para publicar.")
    remote_url = remote_result.stdout.strip()
    if azure_repository(remote_url):
        raise FactoryError("La publicación de PR de Azure Repos requiere intervención humana.")
    remote_display, repo_slug = _remote_identity(remote_url)
    if shutil.which("gh") is None:
        raise FactoryError("Instala GitHub CLI (gh) para publicar la PR.")
    auth = subprocess.run(["gh", "auth", "status"], cwd=job["worktree"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if auth.returncode:
        raise FactoryError("GitHub CLI no tiene una sesión autenticada.")
    existing = subprocess.run(["gh", "pr", "view", branch, "--json", "url", "-q", ".url"], cwd=job["worktree"], text=True, capture_output=True)
    if existing.returncode == 0 and existing.stdout.strip():
        raise FactoryError(f"Ya existe una PR para esta rama: {existing.stdout.strip()}")
    try:
        confirmation = input(f"Esto hará push del SHA {head} de {branch} a {remote_display} y abrirá una PR borrador en {repo_slug} contra {job['base_branch']}. Escribe PUBLICAR {job['id']} {head[:12]} {remote_display} para aprobar: ").strip()
    except EOFError:
        confirmation = ""
    if confirmation != f"PUBLICAR {job['id']} {head[:12]} {remote_display}":
        raise FactoryError("Publicación cancelada; no se hizo push.")
    gates_pass, _ = run_gate(job_path.parent.parent.parent, job)
    latest_remote = git(worktree, "remote", "get-url", "origin", check=False)
    latest_head = git(worktree, "rev-parse", "HEAD", check=False)
    clean = git(worktree, "status", "--porcelain", "--untracked-files=all", check=False)
    latest_branch = git(worktree, "branch", "--show-current", check=False)
    if latest_remote.returncode or latest_remote.stdout.strip() != remote_url:
        raise FactoryError("El remote origin cambió tras la aprobación; no se hizo push.")
    if (latest_head.returncode or latest_head.stdout.strip() != head or clean.returncode or clean.stdout.strip()
            or latest_branch.returncode or latest_branch.stdout.strip() != branch or not gates_pass):
        raise FactoryError("El trabajo cambió tras la aprobación; no se hizo push. Repite gates y revisiones.")
    push = subprocess.run(["git", "push", remote_url, f"{head}:refs/heads/{branch}"], cwd=job["worktree"], text=True, capture_output=True)
    if push.returncode:
        raise FactoryError("El push falló; no se creó ninguna PR. Revisa la salida de GitHub CLI y la conectividad.")
    published = git(worktree, "ls-remote", remote_url, f"refs/heads/{branch}", check=False)
    published_sha = published.stdout.split()[0] if published.returncode == 0 and published.stdout.split() else ""
    if published_sha != head:
        raise FactoryError("La rama remota no coincide con el SHA revisado; no se creó la PR.")
    pr = subprocess.run(
        ["gh", "pr", "create", "--draft", "--repo", repo_slug, "--base", job["base_branch"], "--head", branch,
         "--title", job["title"].replace("\n", " ")[:180], "--body", f"Trabajo DevForge {job['id']}. Pendiente de aprobación humana."],
        cwd=job["worktree"], text=True, capture_output=True,
    )
    if pr.returncode:
        raise FactoryError("La rama quedó publicada, pero GitHub no creó la PR. Revisa la salida de GitHub CLI.")
    job["pull_request"] = pr.stdout.strip()
    pr_head = subprocess.run(["gh", "pr", "view", job["pull_request"], "--repo", repo_slug, "--json", "headRefOid", "-q", ".headRefOid"], cwd=job["worktree"], text=True, capture_output=True)
    if pr_head.returncode or pr_head.stdout.strip() != head:
        job["pull_request_head_mismatch"] = True
        job["status"] = "blocked"
        job["block_reason"] = "El SHA de la PR difiere del SHA revisado; requiere intervención humana."
        write_job(job_path, job)
        raise FactoryError(f"Se creó la PR borrador {job['pull_request']}, pero su SHA no coincide con el revisado. No la fusiones; requiere revisión humana.")
    job["pull_request_head_mismatch"] = False
    write_job(job_path, job)
    return job["pull_request"]


def _remote_identity(value: str) -> tuple[str, str]:
    """Valida un remote GitHub sin secretos incrustados y devuelve destino visible y repo gh."""
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise FactoryError("El remote contiene caracteres de control y no se puede aprobar.")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme:
        if parsed.scheme not in {"https", "ssh", "git+ssh"} or not parsed.hostname or parsed.password or parsed.query or parsed.fragment:
            raise FactoryError("El remote debe ser HTTPS/SSH y no puede contener credenciales, query ni fragmentos; usa un credential helper.")
        if parsed.scheme == "https" and parsed.username:
            raise FactoryError("No se permiten credenciales dentro de la URL remota; usa un credential helper.")
        if parsed.scheme in {"ssh", "git+ssh"} and parsed.username not in (None, "git"):
            raise FactoryError("El usuario SSH del remote debe ser git.")
        host = parsed.hostname.lower()
        path = parsed.path.strip("/")
        try:
            port = parsed.port
        except ValueError as exc:
            raise FactoryError("El remote tiene un puerto inválido.") from exc
        if port:
            host_display = f"{host}:{port}"
        else:
            host_display = host
        display = urllib.parse.urlunsplit((parsed.scheme, ("git@" if parsed.scheme in {"ssh", "git+ssh"} else "") + host_display, "/" + path, "", ""))
    else:
        match = re.fullmatch(r"git@([A-Za-z0-9.-]+):([^?#]+)", value)
        if not match:
            raise FactoryError("El formato del remote no es compatible para abrir PR de GitHub.")
        host, path = match.groups()
        host = host.lower()
        display = f"git@{host}:{path}"
    path = path.removesuffix(".git")
    pieces = path.split("/")
    if len(pieces) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) and part not in {".", ".."} for part in pieces):
        raise FactoryError("El remote debe identificar exactamente un repositorio owner/repo.")
    repo_slug = "/".join(pieces) if host == "github.com" else f"{host}/" + "/".join(pieces)
    return display, repo_slug

