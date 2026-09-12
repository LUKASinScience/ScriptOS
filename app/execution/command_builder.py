import shutil

from app.core.tool import ParameterType, Tool
from app.environments.venv_manager import env_python

_INTERPRETER_BIN = {"python": "python3", "r": "Rscript", "bash": "bash"}


def interpreter_bin(tool: Tool, env_name: str | None = None) -> str:
    """env_name selects one of ScriptOS's own managed venvs instead of the system
    interpreter — only meaningful for python tools; R has no equivalent yet."""
    if env_name and tool.interpreter == "python":
        return str(env_python(env_name))
    return _INTERPRETER_BIN.get(tool.interpreter, tool.interpreter)


def interpreter_available(tool: Tool, env_name: str | None = None) -> bool:
    return shutil.which(interpreter_bin(tool, env_name)) is not None


def build_command(tool: Tool, values: dict, env_name: str | None = None) -> list[str]:
    """Build the argv list that will be executed. Never shell=True."""
    cmd = [interpreter_bin(tool, env_name), tool.script_path]
    for param in tool.parameters:
        value = values.get(param.name, param.default)
        if value is None or value == "":
            continue
        if param.param_type == ParameterType.BOOL:
            if value:
                cmd.append(param.flag)
        else:
            cmd.extend([param.flag, str(value)])
    return cmd
