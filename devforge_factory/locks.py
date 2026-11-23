"""Bloqueos de archivo entre procesos, con la misma semántica en POSIX y Windows."""

import errno
import os
import time

from .core import FactoryError

LOCK_RETRY_SECONDS = 0.05

if os.name == "nt":
    import msvcrt

    def _try_lock(descriptor):
        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EDEADLK):
                return False
            raise
        return True
else:
    import fcntl

    def _try_lock(descriptor):
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True


def open_lock(path):
    """Abre el archivo de bloqueo sin seguir enlaces simbólicos."""
    # Windows no tiene O_NOFOLLOW: la comprobación previa cubre ambos sistemas.
    if path.is_symlink():
        raise FactoryError("El archivo de bloqueo no puede ser un enlace simbólico.")
    return os.open(path, getattr(os, "O_NOFOLLOW", 0) | os.O_CREAT | os.O_RDWR, 0o600)


def acquire(descriptor, blocking=True):
    """Toma el bloqueo exclusivo; se libera al cerrar el descriptor.

    Sin `blocking` lanza BlockingIOError si otro proceso lo tiene.
    """
    while not _try_lock(descriptor):
        if not blocking:
            raise BlockingIOError("El bloqueo está tomado por otro proceso.")
        time.sleep(LOCK_RETRY_SECONDS)
