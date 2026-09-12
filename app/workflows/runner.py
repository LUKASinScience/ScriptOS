"""Runs a saved workflow's scripts one after another, wiring each step's declared
output location into the next step's first file/directory input parameter."""
from pathlib import Path
from typing import Callable

from app.core.tool import ParameterType
from app.discovery.file_heuristics import is_output_param
from app.discovery.python_parser import parse_python_script
from app.discovery.r_parser import parse_r_script
from app.execution.command_builder import build_command
from app.execution.executor import run_tool

_INPUT_TYPES = (ParameterType.FILE_IN, ParameterType.DIRECTORY)


def _parse(script_path: str):
    parser = parse_r_script if script_path.lower().endswith(".r") else parse_python_script
    return parser(script_path)


def _find_output_value(tool, values: dict) -> str | None:
    for param in tool.parameters:
        if param.param_type in (ParameterType.FILE_OUT, ParameterType.DIRECTORY) and is_output_param(param.name):
            return values.get(param.name)
    return None


def run_workflow(steps: list[str], on_line: Callable[[str, str], None] | None = None) -> bool:
    """Runs each step in order; returns True only if every step exits 0.
    Stops at the first failure rather than continuing with stale data."""
    previous_output = None
    for i, script_path in enumerate(steps, start=1):
        tool = _parse(script_path)
        values = {p.name: p.default for p in tool.parameters if p.default is not None}

        if previous_output:
            for param in tool.parameters:
                if param.param_type in _INPUT_TYPES:
                    values[param.name] = previous_output
                    break

        if on_line:
            on_line("stdout", f"── Step {i}/{len(steps)}: {Path(script_path).name} ──")

        command = build_command(tool, values)
        runs_base = Path(script_path).parent / "runs"
        result = run_tool(tool.name, command, runs_base, on_line=on_line)

        if result.exit_code != 0:
            if on_line:
                on_line("stderr", f"Step {i} failed (exit {result.exit_code}) — stopping workflow.")
            return False
        previous_output = _find_output_value(tool, values)
    return True
