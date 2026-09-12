"""Per-parameter validation. Each function returns (level, message) or None if ok is irrelevant."""
from pathlib import Path

from app.core.tool import Parameter, ParameterType

Level = str  # "ok" | "warning" | "error"


def validate_parameter(param: Parameter, value) -> tuple[Level, str]:
    if param.required and (value is None or value == ""):
        return "error", f"{param.label} is required"

    if value in (None, "") and not param.required:
        return "ok", f"{param.label}: not set"

    if param.param_type == ParameterType.FILE_IN:
        path = Path(str(value))
        if not path.exists():
            return "error", f"File not found: {value}"
        if path.stat().st_size == 0:
            return "warning", f"{value} is empty"
        if param.extensions and path.suffix.lstrip(".").lower() not in param.extensions:
            return "warning", f"{value}: unexpected extension (expected {param.extensions})"
        if path.stat().st_size > 10 * 1024**3:
            return "warning", f"{value} is larger than 10 GB"
        return "ok", f"{param.label}: {path.name} ({path.stat().st_size} bytes)"

    if param.param_type == ParameterType.FILE_OUT:
        parent = Path(str(value)).parent
        if not parent.exists():
            return "error", f"Output directory does not exist: {parent}"
        return "ok", f"{param.label}: {value}"

    if param.param_type == ParameterType.DIRECTORY:
        path = Path(str(value))
        if path.exists() and not path.is_dir():
            return "error", f"{value} exists and is not a directory"
        return "ok", f"{param.label}: {value}"

    if param.param_type in (ParameterType.INT, ParameterType.FLOAT):
        try:
            num = float(value)
        except (TypeError, ValueError):
            return "error", f"{param.label}: not a number"
        if param.min_value is not None and num < param.min_value:
            return "error", f"{param.label}: below minimum {param.min_value}"
        if param.max_value is not None and num > param.max_value:
            return "error", f"{param.label}: above maximum {param.max_value}"
        return "ok", f"{param.label}: {value}"

    return "ok", f"{param.label}: {value}"


def validate_all(parameters: list[Parameter], values: dict) -> list[tuple[Level, str]]:
    return [validate_parameter(p, values.get(p.name, p.default)) for p in parameters]


def is_runnable(results: list[tuple[Level, str]]) -> bool:
    return not any(level == "error" for level, _ in results)
