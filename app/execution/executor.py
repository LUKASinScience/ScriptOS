"""Runs a built command as a subprocess and streams output line-by-line via a callback."""
import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import psutil

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


def _monitor_resources(
    proc: subprocess.Popen,
    max_memory_mb: float | None,
    max_cpu_percent: float | None,
    on_line: Callable[[str, str], None] | None,
    stop_event: threading.Event,
):
    """Polls the child's memory/CPU use and kills it if either limit is exceeded.
    Opt-in only (both None = no monitoring at all, zero overhead, unchanged behavior)."""
    if max_memory_mb is None and max_cpu_percent is None:
        return
    try:
        ps_proc = psutil.Process(proc.pid)
    except psutil.NoSuchProcess:
        return

    while not stop_event.is_set() and proc.poll() is None:
        try:
            if max_memory_mb is not None:
                rss_mb = ps_proc.memory_info().rss / (1024 * 1024)
                if rss_mb > max_memory_mb:
                    if on_line:
                        on_line("stderr", f"Memory limit exceeded ({rss_mb:.0f} MB > {max_memory_mb:.0f} MB) — stopping.")
                    proc.kill()
                    return
            if max_cpu_percent is not None:
                cpu = ps_proc.cpu_percent(interval=0.5)
                if cpu > max_cpu_percent:
                    if on_line:
                        on_line("stderr", f"CPU limit exceeded ({cpu:.0f}% > {max_cpu_percent:.0f}%) — stopping.")
                    proc.kill()
                    return
                continue  # cpu_percent(interval=0.5) already paced this iteration
        except psutil.NoSuchProcess:
            return
        stop_event.wait(0.5)


def run_tool(
    tool_name: str,
    command: list[str],
    runs_base: Path,
    on_line: Callable[[str, str], None] | None = None,
    on_process_started: Callable[[subprocess.Popen], None] | None = None,
    extra_env: dict[str, str] | None = None,
    max_memory_mb: float | None = None,
    max_cpu_percent: float | None = None,
) -> RunResult:
    """on_line(stream, text) is called for each stdout/stderr line as it arrives.

    stdout and stderr are pumped on separate threads: reading them sequentially
    (stdout to EOF, then stderr) deadlocks once the unread stream's OS pipe
    buffer fills up and the child blocks trying to write to it.

    extra_env (e.g. injected credentials) is merged into the subprocess environment
    only — never written into command.json or shown in the command preview.

    max_memory_mb/max_cpu_percent are opt-in (None = unlimited, the default) —
    this is a safety net against a run going haywire, not a security sandbox;
    a script can still do anything its user account can until a limit is hit.
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

    stop_monitor = threading.Event()
    monitor_thread = threading.Thread(
        target=_monitor_resources, args=(proc, max_memory_mb, max_cpu_percent, on_line, stop_monitor)
    )
    monitor_thread.start()

    stdout_lines, stderr_lines = [], []
    stdout_thread = threading.Thread(target=_pump, args=(proc.stdout, "stdout", stdout_lines, on_line))
    stderr_thread = threading.Thread(target=_pump, args=(proc.stderr, "stderr", stderr_lines, on_line))
    stdout_thread.start()
    stderr_thread.start()
    proc.wait()
    stop_monitor.set()
    stdout_thread.join()
    stderr_thread.join()
    monitor_thread.join()

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
