"""Best-effort static scan for risky code patterns in a Python script.

Not a security boundary — a determined malicious script can always obfuscate
past a simple AST scan. This is a heads-up before running unfamiliar code,
the same spirit as the existing interactive-input warning: flag it, never block it.
Python only; no equivalent AST tooling readily available for R here.
"""
import ast
from pathlib import Path

_RISKY_CALLS = {
    "eval": "runs arbitrary code from a string",
    "exec": "runs arbitrary code from a string",
    "compile": "compiles code from a string at runtime",
    "system": "runs a shell command (os.system)",
    "popen": "runs a shell command",
    "remove": "deletes a file",
    "rmtree": "deletes a directory tree",
    "loads": "deserializes data — pickle/marshal can execute arbitrary code this way",
}
_RISKY_MODULES = {"socket", "ctypes", "pickle", "marshal"}


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def scan_risks(script_path: str) -> list[str]:
    try:
        tree = ast.parse(Path(script_path).read_text())
    except (OSError, SyntaxError):
        return []

    findings: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            if name in _RISKY_CALLS:
                findings.add(f"{name}() — {_RISKY_CALLS[name]}")
            if name == "run" and any(
                isinstance(kw.value, ast.Constant) and kw.arg == "shell" and kw.value.value is True
                for kw in node.keywords
            ):
                findings.add("subprocess.run(..., shell=True) — runs a shell command")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module_names = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            for name in module_names:
                if name in _RISKY_MODULES:
                    findings.add(f"imports {name}")
    return sorted(findings)
