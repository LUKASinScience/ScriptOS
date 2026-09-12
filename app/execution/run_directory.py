from datetime import datetime
from pathlib import Path


def create_run_directory(base: Path, tool_name: str) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = base / f"{stamp}_{tool_name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir
