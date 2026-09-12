"""Small JSON-backed list of recently loaded scripts, so users don't reload every session."""
import json
from pathlib import Path

_STORE_PATH = Path.home() / ".scriptos" / "recent.json"
_MAX_ENTRIES = 8


def load_recent() -> list[dict]:
    try:
        return json.loads(_STORE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return []


def add_recent(name: str, path: str):
    entries = [e for e in load_recent() if e["path"] != path]
    entries.insert(0, {"name": name, "path": path})
    entries = entries[:_MAX_ENTRIES]
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(entries, indent=2))
