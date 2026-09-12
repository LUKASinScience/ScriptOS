"""Regex-based extraction of optparse::make_option() calls into a Tool model.

R has no stdlib AST module available to us, so unlike python_parser this scans
text with balanced-paren matching instead of a real parser.
ponytail: single-call-per-match heuristic, ceiling is make_option calls split
oddly across lines with nested parens in `default=`; upgrade path is a real
R tokenizer if that ever breaks on a real script.
"""
import re
from pathlib import Path

from app.core.tool import Dependency, Parameter, ParameterType, Tool
from app.discovery.file_heuristics import guess_file_type

_BASE_PACKAGES = {
    "base", "utils", "stats", "methods", "graphics", "grDevices",
    "datasets", "tools", "parallel", "compiler", "grid", "splines", "stats4",
}

_MAKE_OPTION_START = re.compile(r"make_option\s*\(")
_FLAGS_RE = re.compile(r'c\(\s*((?:"[^"]*"|\'[^\']*\')(?:\s*,\s*(?:"[^"]*"|\'[^\']*\'))*)\s*\)')
_TYPE_RE = re.compile(r'type\s*=\s*"([^"]+)"')
_ACTION_RE = re.compile(r'action\s*=\s*"([^"]+)"')
_HELP_RE = re.compile(r'help\s*=\s*"([^"]*)"')
_DEFAULT_RE = re.compile(r'default\s*=\s*(.+?)(?:,\s*[a-zA-Z_]+\s*=|$)')
_LIBRARY_RE = re.compile(r'(?:library|require)\s*\(\s*["\']?([A-Za-z0-9._]+)["\']?\s*\)')

_R_TYPE_MAP = {
    "character": ParameterType.STR,
    "double": ParameterType.FLOAT,
    "numeric": ParameterType.FLOAT,
    "integer": ParameterType.INT,
}


def _extract_balanced(text: str, open_paren_index: int) -> str:
    depth = 0
    for i in range(open_paren_index, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return text[open_paren_index + 1:i]
    return text[open_paren_index + 1:]


def _parse_option(call_body: str) -> Parameter | None:
    flags_match = _FLAGS_RE.search(call_body)
    if not flags_match:
        return None
    flags = [a or b for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', flags_match.group(1))]
    long_flag = next((f for f in flags if f.startswith("--")), flags[-1] if flags else None)
    if not long_flag:
        return None
    name = long_flag.lstrip("-").replace("-", "_")

    help_match = _HELP_RE.search(call_body)
    help_text = help_match.group(1) if help_match else ""

    action_match = _ACTION_RE.search(call_body)
    if action_match and action_match.group(1) in ("store_true", "store_false"):
        param_type = ParameterType.BOOL
    else:
        type_match = _TYPE_RE.search(call_body)
        r_type = type_match.group(1) if type_match else "character"
        param_type = _R_TYPE_MAP.get(r_type, ParameterType.STR)
        if param_type == ParameterType.STR:
            param_type = guess_file_type(name, help_text) or ParameterType.STR

    default_match = _DEFAULT_RE.search(call_body)
    default_raw = default_match.group(1).strip() if default_match else None
    default = None if default_raw in (None, "NULL") else default_raw.strip('"\'')

    return Parameter(
        name=name,
        flag=long_flag,
        param_type=param_type,
        label=name.replace("_", " ").title(),
        description=help_text,
        required=default is None,
        default=default,
    )


def _leading_comment_header(source: str) -> str:
    """R has no docstrings — scripts conventionally describe themselves in a leading
    block of '#' comment lines. First non-empty one is used as the description."""
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        break
    return ""


def _detect_dependencies(source: str) -> list[Dependency]:
    names = {m.group(1) for m in _LIBRARY_RE.finditer(source)}
    return [
        Dependency(name=n, conda_install=f"conda install -c conda-forge r-{n.lower()}")
        for n in sorted(names)
        if n not in _BASE_PACKAGES and n != "optparse"
    ]


def parse_r_script(script_path: str) -> Tool:
    path = Path(script_path)
    source = path.read_text()

    parameters: list[Parameter] = []
    for match in _MAKE_OPTION_START.finditer(source):
        body = _extract_balanced(source, match.end() - 1)
        param = _parse_option(body)
        if param:
            parameters.append(param)

    return Tool(
        name=path.stem,
        script_path=str(path),
        interpreter="r",
        parameters=parameters,
        dependencies=_detect_dependencies(source),
        description=_leading_comment_header(source),
        source="argparse_auto",
    )
