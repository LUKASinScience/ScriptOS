"""Runs a built command as a subprocess and streams output line-by-line via a callback."""
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.execution.run_directory import create_run_directory


@dataclass
class RunResult:
    exit_code: int
    duration_seconds: float
    run_dir: Path


def _pump(stream, stream_name: str, sink: list[str], on_line: Callable[[str, str], None] | None):
    for line in stream:
        sink.append(line)
        if on_line:
            on_line(stream_name, line.rstrip("\n"))


def run_tool(
    tool_name: str,
    command: list[str],
    runs_base: Path,
    on_line: Callable[[str, str], None] | None = None,
    on_process_started: Callable[[subprocess.Popen], None] | None = None,
    extra_env: dict[str, str] | None = None,
) -> RunResult:
    """on_line(stream, text) is called for each stdout/stderr line as it arrives.

    stdout and stderr are pumped on separate threads: reading them sequentially
    (stdout to EOF, then stderr) deadlocks once the unread stream's OS pipe
    buffer fills up and the child blocks trying to write to it.

    extra_env (e.g. injected credentials) is merged into the subprocess environment
    only — never written into command.json or shown in the command preview.
    """
    run_dir = create_run_directory(runs_base, tool_name)
    (run_dir / "command.json").write_text(json.dumps({"command": command}, indent=2))

    start = time.monotonic()
    env = {**os.environ, **extra_env} if extra_env else None
    try:
        proc = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,  # a script blocked on input() would otherwise hang forever with no feedback
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
    except OSError as exc:
        # e.g. the interpreter binary (Rscript, python3, ...) isn't installed. Without this,
        # the exception propagates out of the worker thread silently and the UI hangs on
        # "Running..." forever with no error shown.
        duration = time.monotonic() - start
        error_msg = f"Could not start '{command[0]}': {exc}"
        if on_line:
            on_line("stderr", error_msg)
        (run_dir / "stderr.log").write_text(error_msg)
        (run_dir / "command.json").write_text(
            json.dumps({"command": command, "exit_code": -1, "duration_seconds": round(duration, 2), "error": error_msg}, indent=2)
        )
        return RunResult(exit_code=-1, duration_seconds=duration, run_dir=run_dir)

    if on_process_started:
        on_process_started(proc)

    stdout_lines, stderr_lines = [], []
    stdout_thread = threading.Thread(target=_pump, args=(proc.stdout, "stdout", stdout_lines, on_line))
    stderr_thread = threading.Thread(target=_pump, args=(proc.stderr, "stderr", stderr_lines, on_line))
    stdout_thread.start()
    stderr_thread.start()
    proc.wait()
    stdout_thread.join()
    stderr_thread.join()

    duration = time.monotonic() - start
    (run_dir / "stdout.log").write_text("".join(stdout_lines))
    (run_dir / "stderr.log").write_text("".join(stderr_lines))
    (run_dir / "command.json").write_text(
        json.dumps(
            {"command": command, "exit_code": proc.returncode, "duration_seconds": round(duration, 2)},
            indent=2,
        )
    )
    return RunResult(exit_code=proc.returncode, duration_seconds=duration, run_dir=run_dir)
