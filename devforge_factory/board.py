"""Cola cooperativa por repositorio y tablero local de solo lectura."""

import fcntl
import html
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .core import FactoryError, config_for, jobs, now

DEFAULT_LEASE_HOURS = 12


def _claimed_at(value):
    if not isinstance(value, str):
        raise FactoryError("El registro de reservas es inválido.")
    try:
        moment = datetime.fromisoformat(value)
    except ValueError as exc:
        raise FactoryError("El registro de reservas contiene una fecha inválida.") from exc
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _prune(leases, config):
    """Libera reservas abandonadas; una sesión caída no bloquea la cola para siempre."""
    hours = config.get("reservation_ttl_hours", DEFAULT_LEASE_HOURS)
    if type(hours) is not int or hours < 1:
        raise FactoryError("reservation_ttl_hours debe ser un entero positivo.")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stale = [job_id for job_id, value in leases.items() if _claimed_at(value) < cutoff]
    for job_id in stale:
        del leases[job_id]
    return stale


def _directory(root):
    folder = root / ".devforge/jobs"
    if folder.is_symlink():
        raise FactoryError("La carpeta de trabajos no puede ser un enlace.")
    folder.mkdir(mode=0o700, exist_ok=True)
    return folder


def _save(path, content):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(content)
    os.replace(stream.name, path)


@contextmanager
def _queue(cwd):
    root, config = config_for(cwd)
    folder = _directory(root)
    lock = os.open(folder / ".queue.lock", os.O_NOFOLLOW | os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = folder / ".reservas.json"
        if state.is_symlink():
            raise FactoryError("Ruta de reservas inválida.")
        try:
            leases = json.loads(state.read_text()) if state.exists() else {}
        except (ValueError, OSError) as exc:
            raise FactoryError("No se pudieron leer las reservas.") from exc
        if not isinstance(leases, dict):
            raise FactoryError("El registro de reservas es inválido.")
        stale = _prune(leases, config)
        if stale:
            _save(state, json.dumps(leases) + "\n")
        records = sorted((job for _, job in jobs(root)), key=lambda j: (j.get("created_at", ""), j["id"]))
        yield records, leases, config, state, stale
    finally:
        os.close(lock)


def claim_next(cwd, job_id=None):
    with _queue(cwd) as (records, leases, config, state, _):
        limit = config.get("concurrency", 2)
        if type(limit) is not int or limit < 1:
            raise FactoryError("concurrency debe ser un entero positivo.")
        if len(leases) >= limit:
            raise FactoryError("Se alcanzó el límite de trabajos reservados.")
        for job in records:
            if job_id is not None and job["id"] != job_id:
                continue
            if job["status"] == "queued" and job["id"] not in leases:
                leases[job["id"]] = now()
                _save(state, json.dumps(leases) + "\n")
                return job["id"]
        raise FactoryError("No hay trabajos pendientes sin reservar.")


def release(cwd, job_id):
    with _queue(cwd) as (_, leases, _, state, _):
        if job_id not in leases:
            raise FactoryError("El trabajo no tiene una reserva activa.")
        del leases[job_id]
        _save(state, json.dumps(leases) + "\n")


def show_queue(cwd):
    with _queue(cwd) as (records, leases, _, _, stale):
        for job in records:
            suffix = " (reservado)" if job["id"] in leases else ""
            print(f"{job['id']} [{job['status']}] {job['title']}{suffix}")
        if not records:
            print("La cola está vacía.")
        if stale:
            print(f"Reservas caducadas liberadas: {len(stale)}.")


def dashboard(cwd):
    with _queue(cwd) as (records, leases, _, state, _):
        rows = []
        for j in records:
            rounds = f"{j.get('round', 1)}/{j.get('max_rounds', 1)}"
            values = (j["id"], j["title"], j["source"], j["status"], rounds,
                      "Sí" if j["id"] in leases else "No", j.get("updated_at", ""))
            rows.append("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in values) + "</tr>")
        target = state.parent / "dashboard.html"
        headers = ("Trabajo", "Solicitud", "Origen", "Estado", "Ronda", "Reservado", "Último cambio")
        content = """<!doctype html><html lang="es"><meta charset="utf-8"><meta http-equiv="refresh" content="5"><title>DevForge · Trabajos</title>
<style>body{font:16px system-ui;margin:3vw;color:#172331}table{border-collapse:collapse}td,th{padding:.6rem;border-bottom:1px solid #bac7cc;text-align:left}th{background:#eaf1f4}</style>
<h1>Trabajos del proyecto</h1>"""
        content += f"<p>{len(records)} trabajos · Actualizado {now()} · Se recarga cada 5 s</p><table><thead><tr>"
        content += "".join(f'<th scope="col">{h}</th>' for h in headers) + "</tr></thead><tbody>"
        _save(target, content + "".join(rows) + "</tbody></table></html>")
        return target
