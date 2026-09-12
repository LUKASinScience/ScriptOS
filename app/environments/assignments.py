"""Remembers which environment and which credential set a given script is set up
to use, so both are pre-selected next time and the management page can show
what's assigned to what — for both environments and the secrets wallet."""
import json
from pathlib import Path

_PATH = Path.home() / ".scriptos" / "assignments.json"


def _load() -> dict[str, dict[str, str]]:
    """script_path -> {"env": name, "credentials": name}"""
    try:
        return json.loads(_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, dict[str, str]]):
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2))


def _set(script_path: str, field: str, value: str | None):
    data = _load()
    entry = data.setdefault(script_path, {})
    if value:
        entry[field] = value
    else:
        entry.pop(field, None)
    if not entry:
        data.pop(script_path, None)
    _save(data)


def get_assigned_env(script_path: str) -> str | None:
    return _load().get(script_path, {}).get("env")


def set_assigned_env(script_path: str, env_name: str | None):
    _set(script_path, "env", env_name)


def get_assigned_credentials(script_path: str) -> str | None:
    return _load().get(script_path, {}).get("credentials")


def set_assigned_credentials(script_path: str, set_name: str | None):
    _set(script_path, "credentials", set_name)


def scripts_using_env(env_name: str) -> list[str]:
    return sorted(path for path, entry in _load().items() if entry.get("env") == env_name)


def scripts_using_credentials(set_name: str) -> list[str]:
    return sorted(path for path, entry in _load().items() if entry.get("credentials") == set_name)
