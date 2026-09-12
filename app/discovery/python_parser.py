"""AST-based extraction of argparse.add_argument() calls into a Tool model."""
import ast
import sys
from pathlib import Path

from app.core.tool import Dependency, Parameter, ParameterType, Tool
from app.discovery.file_heuristics import guess_file_type

_STDLIB = sys.stdlib_module_names

_TYPE_MAP = {
    "int": ParameterType.INT,
    "float": ParameterType.FLOAT,
    "str": ParameterType.STR,
}


def _literal(node: ast.expr | None):
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def _parse_call(call: ast.Call) -> Parameter | None:
    flags = [a.value for a in call.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
    if not flags:
        return None
    flag = next((f for f in flags if f.startswith("--")), flags[0])
    name = flag.lstrip("-").replace("-", "_")

    kwargs = {kw.arg: kw for kw in call.keywords if kw.arg}

    help_text = _literal(kwargs["help"].value) if "help" in kwargs else ""
    action = _literal(kwargs["action"].value) if "action" in kwargs else None
    if action in ("store_true", "store_false"):
        param_type = ParameterType.BOOL
    elif "choices" in kwargs:
        param_type = ParameterType.CHOICE
    else:
        type_node = kwargs.get("type")
        type_name = type_node.value.id if type_node and isinstance(type_node.value, ast.Name) else "str"
        if type_name in ("int", "float"):
            param_type = _TYPE_MAP[type_name]
        else:
            param_type = guess_file_type(name, help_text or "") or ParameterType.STR

    return Parameter(
        name=name,
        flag=flag,
        param_type=param_type,
        label=name.replace("_", " ").title(),
        description=help_text or "",
        required=bool(_literal(kwargs["required"].value)) if "required" in kwargs else False,
        default=_literal(kwargs["default"].value) if "default" in kwargs else None,
        choices=_literal(kwargs["choices"].value) or [] if "choices" in kwargs else [],
    )


def _detect_dependencies(tree: ast.AST) -> list[Dependency]:
    """Top-level imported module names that aren't part of the standard library."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return [Dependency(name=n, pip_install=f"pip install {n}") for n in sorted(names) if n not in _STDLIB]


def parse_python_script(script_path: str) -> Tool:
    """Parse a Python CLI script's argparse calls into a Tool definition."""
    path = Path(script_path)
    source = path.read_text()
    tree = ast.parse(source)

    parameters: list[Parameter] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            param = _parse_call(node)
            if param:
                parameters.append(param)

    docstring = ast.get_docstring(tree) or ""
    return Tool(
        name=path.stem,
        script_path=str(path),
        interpreter="python",
        parameters=parameters,
        dependencies=_detect_dependencies(tree),
        description=docstring.strip().splitlines()[0] if docstring.strip() else "",
        source="argparse_auto",
    )
