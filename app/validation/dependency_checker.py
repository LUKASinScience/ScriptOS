"""Checks whether the interpreter and each detected package are actually available."""
import shutil
import subprocess

from app.core.tool import Dependency, Tool
from app.execution.command_builder import interpreter_bin

_INTERPRETER_INSTALL_HINTS = {
    "python": "Install Python from python.org, or run: brew install python",
    "r": "Install R: brew install r  (or download from cran.r-project.org)",
}


def check_interpreter(tool: Tool, env_name: str | None = None) -> tuple[bool, str]:
    """Returns (available, install_hint). install_hint is empty when available."""
    bin_name = interpreter_bin(tool, env_name)
    if shutil.which(bin_name):
        return True, ""
    hint = _INTERPRETER_INSTALL_HINTS.get(tool.interpreter, f"Install '{bin_name}' and make sure it's on PATH.")
    return False, hint


def _check_python_package(name: str, python_bin: str) -> bool | None:
    """Checked against `python_bin` itself — the interpreter the script will actually run
    under — not ScriptOS's own venv, which is a different environment entirely."""
    if not shutil.which(python_bin):
        return None
    try:
        result = subprocess.run([python_bin, "-c", f"import {name}"], capture_output=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return None


def _check_r_package(name: str) -> bool | None:
    """None means "can't check" (R itself isn't installed)."""
    if not shutil.which("Rscript"):
        return None
    probe = f'quit(status=if(requireNamespace("{name}",quietly=TRUE)) 0 else 1)'
    try:
        result = subprocess.run(["Rscript", "-e", probe], capture_output=True, timeout=10)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return None


def check_dependencies(tool: Tool, env_name: str | None = None) -> list[tuple[Dependency, bool | None]]:
    """Returns (dependency, status) pairs. status is True/False/None (unknown)."""
    if tool.interpreter == "python":
        python_bin = interpreter_bin(tool, env_name)
        return [(dep, _check_python_package(dep.name, python_bin)) for dep in tool.dependencies]
    return [(dep, _check_r_package(dep.name)) for dep in tool.dependencies]
