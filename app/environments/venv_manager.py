"""Creates and manages isolated Python virtual environments for running scripts,
so dependencies for one tool never clash with another or with the system Python."""
import shutil
import subprocess
from pathlib import Path
from typing import Callable

ENVS_DIR = Path.home() / ".scriptos" / "envs"


def list_envs() -> list[str]:
    if not ENVS_DIR.exists():
        return []
    return sorted(p.name for p in ENVS_DIR.iterdir() if env_python(p.name).exists())


def env_python(name: str) -> Path:
    base = ENVS_DIR / name
    windows_python = base / "Scripts" / "python.exe"
    return windows_python if windows_python.exists() else base / "bin" / "python3"


def env_dir(name: str) -> Path:
    """Where this environment physically lives on disk — entirely inside ScriptOS's
    own data directory, never a system-wide location."""
    return ENVS_DIR / name


def create_env(name: str) -> tuple[bool, str]:
    system_python = shutil.which("python3")
    if not system_python:
        return False, "No system python3 found to create the environment with."
    target = ENVS_DIR / name
    if target.exists():
        return False, f"An environment named '{name}' already exists."
    ENVS_DIR.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([system_python, "-m", "venv", str(target)], capture_output=True, text=True)
    if result.returncode != 0:
        shutil.rmtree(target, ignore_errors=True)
        return False, result.stderr.strip() or "venv creation failed."
    return True, ""


def delete_env(name: str):
    shutil.rmtree(ENVS_DIR / name, ignore_errors=True)


def list_installed(name: str) -> list[str]:
    try:
        result = subprocess.run(
            [str(env_python(name)), "-m", "pip", "list", "--format=freeze"],
            capture_output=True, text=True, timeout=15,
        )
        return sorted(line.split("==")[0] for line in result.stdout.splitlines() if line)
    except (subprocess.TimeoutExpired, OSError):
        return []


def install_packages(name: str, packages: list[str], on_line: Callable[[str], None] | None = None) -> bool:
    python_bin = env_python(name)
    proc = subprocess.Popen(
        [str(python_bin), "-m", "pip", "install", *packages],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    for line in proc.stdout:
        if on_line:
            on_line(line.rstrip("\n"))
    proc.wait()
    return proc.returncode == 0
