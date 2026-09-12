"""Named credential sets for scripts that need login/API secrets.

Everything stays inside ScriptOS's own data directory (~/.scriptos) — no OS
keychain, no external service. Secret values are encrypted at rest with a
locally-generated key file (owner-read-only); ScriptOS never touches macOS
Keychain, Windows Credential Locker, or any other system credential store.
"""
import json
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

_DIR = Path.home() / ".scriptos"
_KEY_PATH = _DIR / "secret.key"
_STORE_PATH = _DIR / "credentials.enc.json"


def _get_key() -> bytes:
    _DIR.mkdir(parents=True, exist_ok=True)
    if not _KEY_PATH.exists():
        _KEY_PATH.write_bytes(Fernet.generate_key())
        os.chmod(_KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 0600, this user only
    return _KEY_PATH.read_bytes()


def _fernet() -> Fernet:
    return Fernet(_get_key())


def _load_store() -> dict[str, dict[str, str]]:
    """set_name -> {key: encrypted_value}"""
    try:
        return json.loads(_STORE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_store(store: dict[str, dict[str, str]]):
    _DIR.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(store, indent=2))
    os.chmod(_STORE_PATH, stat.S_IRUSR | stat.S_IWUSR)


def list_sets() -> list[str]:
    return sorted(_load_store().keys())


def get_keys(set_name: str) -> list[str]:
    return sorted(_load_store().get(set_name, {}).keys())


def set_secret(set_name: str, key: str, value: str):
    store = _load_store()
    store.setdefault(set_name, {})[key] = _fernet().encrypt(value.encode()).decode()
    _save_store(store)


def get_secret(set_name: str, key: str) -> str | None:
    encrypted = _load_store().get(set_name, {}).get(key)
    if encrypted is None:
        return None
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return None


def delete_key(set_name: str, key: str):
    store = _load_store()
    if key in store.get(set_name, {}):
        del store[set_name][key]
        if not store[set_name]:
            del store[set_name]
        _save_store(store)


def delete_set(set_name: str):
    store = _load_store()
    if set_name in store:
        del store[set_name]
        _save_store(store)


def resolve_env(set_name: str) -> dict[str, str]:
    """key -> secret value, ready to merge into a subprocess environment."""
    return {key: get_secret(set_name, key) or "" for key in get_keys(set_name)}
