"""Ciclo híbrido: los agentes producen evidencia y el núcleo controla cada ronda."""

from contextlib import contextmanager
import os
from pathlib import Path
import re

from .core import FactoryError, TRANSITIONS, git, now, read_job, run_gate, write_job
from .locks import acquire, open_lock


MANDATORY = ("review-code.md", "review-security.md", "review-qa.md")
VISUAL = ("review-ui.md", "review-ux.md")
REPORTS = ("quality-gates.md", *MANDATORY, *VISUAL, "decision.md")
ARCHIVED = ("intake.md", "plan.md", "build.md", *REPORTS)


@contextmanager
def job_lock(folder):
    path = folder / ".lifecycle.lock"
    if path.is_symlink():
        raise FactoryError("El bloqueo del trabajo no puede ser un enlace simbólico.")
    lock = open_lock(path)
    try:
        try:
            acquire(lock, blocking=False)
        except BlockingIOError as exc:
            raise FactoryError("Otro proceso está operando sobre este trabajo.") from exc
        yield
    finally:
        os.close(lock)


def move(folder, job, status, **fields):
    if status != job["status"] and status not in TRANSITIONS[job["status"]]:
        raise FactoryError(f"Transición no permitida: {job['status']} → {status}")
    job.update(fields, status=status)
    write_job(folder, job)


def report_text(folder, name):
    path = folder / name
    if path.is_symlink():
        raise FactoryError(f"Informe enlazado no permitido: {name}")
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def reviewers(folder):
    intake = report_text(folder, "intake.md")
    surface = re.search(r"^SUPERFICIES:\s*([^\n]*)", intake, re.MULTILINE | re.IGNORECASE)
    return MANDATORY + (VISUAL if surface and "interfaz" in surface[1].lower() else ())


def snapshot(folder, job):
    target = folder / f"round-{job.get('round', 1)}"
    if target.is_symlink():
        raise FactoryError("La carpeta de ronda no puede ser un enlace simbólico.")
    target.mkdir(exist_ok=True)
    for name in ARCHIVED:
        data = report_text(folder, name)
        if data:
            atomic_text(target, name, data)
    return target


def atomic_text(folder, name, data):
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=folder, delete=False) as stream:
        stream.write(data)
    Path(stream.name).replace(folder / name)


def clear_reports(folder):
    for name in REPORTS:
        (folder / name).unlink(missing_ok=True)


def pause(folder, job):
    if job["status"] != "paused":
        move(folder, job, "paused", paused_from=job["status"])
    return f"Trabajo pausado: {job['id']}"


def resume(folder, job):
    if job["status"] == "paused":
        previous = job.get("paused_from")
        if not previous:
            previous = "review" if job.get("reviewed_sha") else "planned"
        move(folder, job, previous, paused_from=None)
        if previous in {"queued", "planned"}:
            return f"Etapa de planificación ({previous}). Continúa la admisión y el plan."
    if job["status"] == "planned":
        move(folder, job, "working")
    if job["status"] == "working":
        return f"Etapa de construcción, ronda {job.get('round', 1)}. Worktree: {job['worktree']}"
    if job["status"] == "review":
        missing = [name for name in (*reviewers(folder), "decision.md") if not report_text(folder, name)]
        return "Etapa de revisión. " + ("Pendientes: " + ", ".join(missing) if missing else "Verifica dictámenes y solicita decisión humana.")
    if job["status"] == "blocked":
        raise FactoryError(job.get("block_reason") or "Trabajo bloqueado. Consulta la ronda y usa rework si corresponde.")
    if job["status"] == "queued":
        return "Etapa de admisión pendiente. Ejecuta plan para este trabajo."
    raise FactoryError("El trabajo ya terminó.")


def review(folder, job, root):
    worktree = Path(job["worktree"])
    if job["status"] == "review":
        verify_head(job)
        return resume(folder, job)
    if job["status"] != "working":
        raise FactoryError("La revisión requiere una ronda de construcción activa.")
    before = git(worktree, "rev-parse", "HEAD").stdout.strip()
    okay, report = run_gate(root, job)
    head = git(worktree, "rev-parse", "HEAD").stdout.strip()
    if before != head or git(worktree, "branch", "--show-current").stdout.strip() != job["branch"]:
        okay, report = False, "working-tree: FAIL; cambió la rama o el commit durante los gates."
    clear_reports(folder)
    atomic_text(folder, "quality-gates.md", f"# Quality Gates\nHEAD: {head}\n\n{report}\n")
    snapshot(folder, job)
    move(folder, job, "review" if okay else "blocked",
         reviewed_sha=head if okay else None, gate_pass=okay,
         block_reason=None if okay else "Gate fallido. Consulta quality-gates.md y ejecuta rework.")
    if not okay:
        raise FactoryError(report)
    return f"Gates aprobados en la ronda {job.get('round', 1)}. Revisa el SHA {head}."


def rework(folder, job):
    if job["status"] not in {"blocked", "review"} or job.get("pull_request_head_mismatch") or job.get("pull_request"):
        raise FactoryError("Solo se puede reabrir una ronda revisada antes de publicar.")
    if job.get("rounds_exhausted"):
        raise FactoryError("Límite de rondas alcanzado. Se requiere intervención humana.")
    number, maximum = job.get("round", 1), job.get("max_rounds", 3)
    target = snapshot(folder, job)
    if number >= maximum:
        reason = f"Se agotaron las {maximum} rondas. Entrega {target.name} a la persona responsable."
        move(folder, job, "blocked", rounds_exhausted=True, block_reason=reason, reviewed_sha=None)
        raise FactoryError(reason)
    move(folder, job, "working", round=number + 1, gate_pass=None, reviewed_sha=None, block_reason=None)
    clear_reports(folder)
    return f"Ronda {number + 1}/{maximum}. Entrega los hallazgos de {target} al constructor."


def verify_head(job):
    if job.get("pull_request_head_mismatch"):
        raise FactoryError("La PR requiere intervención humana.")
    worktree = Path(job["worktree"])
    sha = git(worktree, "rev-parse", "HEAD").stdout.strip()
    if sha != job.get("reviewed_sha") or git(worktree, "branch", "--show-current").stdout.strip() != job["branch"]:
        raise FactoryError("El SHA o la rama difiere de la revisión. Solicita rework.")
    if git(worktree, "status", "--porcelain", "--untracked-files=all").stdout.strip():
        raise FactoryError("Hay cambios sin revisar en el worktree.")
    return sha


def acceptance(folder, job):
    if job["status"] != "review" or job.get("rounds_exhausted"):
        raise FactoryError("Se requiere una revisión vigente.")
    sha = verify_head(job)
    gate = report_text(folder, "quality-gates.md")
    if job.get("gate_pass") is False or "FAIL" in gate or "working-tree: PASS" not in gate:
        raise FactoryError("Falta el gate aprobado.")
    if "tests-configured" in job.get("quality_gates", []) and "test-command: PASS" not in gate:
        raise FactoryError("Falta el gate de pruebas.")
    for name in (*reviewers(folder), "decision.md"):
        verdict = "DECISION: APROBAR" if name == "decision.md" else "APTO"
        if report_text(folder, name).splitlines()[:2] != [verdict, f"HEAD: {sha}"]:
            raise FactoryError(f"Falta aprobación para el SHA vigente en {name}.")
    return sha


def close(folder, job):
    if job["status"] == "done":
        return "El trabajo ya se cerró."
    sha = acceptance(folder, job)
    phrase = f"CERRAR {job['id']} {sha[:12]}"
    try:
        answer = input(f"Cierre local del trabajo. Escribe {phrase} para confirmar: ")
    except EOFError:
        answer = ""
    if answer.strip() != phrase:
        raise FactoryError("Cierre cancelado.")
    if acceptance(folder, read_job(folder)) != sha:
        raise FactoryError("La evidencia cambió después de la confirmación.")
    snapshot(folder, job)
    archived = ""
    if job.get("source") == "openspec":
        from .openspec import archive_job

        archived = "\n" + archive_job(folder.parents[2], folder, job)
    move(folder, job, "done", closed_at=now(), closed_sha=sha)
    return f"Trabajo cerrado localmente en {sha}. No se modificó ninguna referencia remota." + archived
