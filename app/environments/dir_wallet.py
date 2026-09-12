"""Named, saved directories — the counterpart to the environment wallet, so a
power-terminal user can pick 'this env' + 'this directory' and jump straight
into working there, instead of keeping a terminal tab open just to stay put."""
import json
from pathlib import Path

_PATH = Path.home() / ".scriptos" / "directories.json"


def _load() -> dict[str, str]:
    """name -> absolute path"""
    try:
        return json.loads(_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, str]):
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2))


def list_dirs() -> list[str]:
    return sorted(_load().keys())


def get_path(name: str) -> str | None:
    return _load().get(name)


def add_dir(name: str, path: str):
    data = _load()
    data[name] = str(Path(path).resolve())
    _save(data)


def delete_dir(name: str):
    data = _load()
    data.pop(name, None)
    _save(data)
