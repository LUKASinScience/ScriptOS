"""Background QThreads shared across pages: running a tool, installing
packages into an environment, running a saved workflow. Kept together since
they're generic execution primitives, not page-specific UI."""
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.environments import venv_manager
from app.execution.executor import run_tool
from app.workflows.runner import run_workflow


class RunWorker(QThread):
    line_received = Signal(str, str)
    finished_run = Signal(int, float)

    def __init__(
        self,
        tool_name: str,
        command: list[str],
        runs_base: Path,
        extra_env: dict[str, str] | None = None,
        max_memory_mb: float | None = None,
        max_cpu_percent: float | None = None,
    ):
        super().__init__()
        self.tool_name, self.command, self.runs_base = tool_name, command, runs_base
        self.extra_env = extra_env
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.run_dir: Path | None = None
        self._proc = None

    def run(self):
        # Any uncaught exception here would otherwise die silently inside the QThread and
        # leave the UI stuck on "Running..." forever with zero feedback — always emit.
        try:
            result = run_tool(
                self.tool_name, self.command, self.runs_base,
                on_line=lambda stream, text: self.line_received.emit(stream, text),
                on_process_started=lambda proc: setattr(self, "_proc", proc),
                extra_env=self.extra_env,
                max_memory_mb=self.max_memory_mb,
                max_cpu_percent=self.max_cpu_percent,
            )
            self.run_dir = result.run_dir
            self.finished_run.emit(result.exit_code, result.duration_seconds)
        except Exception as exc:
            self.line_received.emit("stderr", f"ScriptOS internal error: {exc}")
            self.finished_run.emit(-1, 0.0)

    def stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()


class InstallWorker(QThread):
    line_received = Signal(str)
    finished_install = Signal(bool)

    def __init__(self, env_name: str, packages: list[str]):
        super().__init__()
        self.env_name, self.packages = env_name, packages

    def run(self):
        try:
            ok = venv_manager.install_packages(self.env_name, self.packages, on_line=self.line_received.emit)
        except Exception as exc:
            self.line_received.emit(f"ScriptOS internal error: {exc}")
            ok = False
        self.finished_install.emit(ok)


class WorkflowRunner(QThread):
    line_received = Signal(str, str)
    finished_workflow = Signal(bool)

    def __init__(self, steps: list[str]):
        super().__init__()
        self.steps = steps

    def run(self):
        try:
            ok = run_workflow(self.steps, on_line=lambda s, t: self.line_received.emit(s, t))
        except Exception as exc:
            self.line_received.emit("stderr", f"ScriptOS internal error: {exc}")
            ok = False
        self.finished_workflow.emit(ok)
