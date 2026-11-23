"""Utilidades compartidas por las pruebas."""

import os
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

IS_WINDOWS = os.name == "nt"
# En Windows no hay sandbox con /usr/bin/python3: las pruebas del gate usan el intérprete actual.
GATE_PYTHON = sys.executable if IS_WINDOWS else "python3"


@lru_cache(maxsize=1)
def symlinks_available():
    """Windows solo permite crear enlaces simbólicos con privilegios o modo desarrollador."""
    with tempfile.TemporaryDirectory() as temp:
        try:
            (Path(temp) / "enlace").symlink_to(Path(temp) / "destino")
        except (OSError, NotImplementedError):
            return False
    return True


@lru_cache(maxsize=1)
def bwrap_ready():
    """Comprueba si el sandbox de gates puede crearse en este entorno."""
    binary = shutil.which("bwrap")
    if not binary:
        return False
    probe = [
        binary, "--unshare-all", "--die-with-parent",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
        "--proc", "/proc", "--dev", "/dev", "--", "true",
    ]
    try:
        result = subprocess.run(probe, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0
