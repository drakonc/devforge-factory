"""Utilidades compartidas por las pruebas."""

import shutil
import subprocess
from functools import lru_cache


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
