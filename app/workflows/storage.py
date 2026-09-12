"""Saved workflows: an ordered list of scripts to run one after another.

Deliberately not a DAG engine — one linear chain, each step's declared output
location is fed into the next step's first file/directory input. That covers
the common "script A's output feeds script B" case without the complexity of
branching, conditions, or resumable execution that a real workflow engine
(Snakemake, Nextflow) exists for.
"""
import json
from pathlib import Path

_PATH = Path.home() / ".scriptos" / "workflows.json"


def _load() -> dict[str, list[str]]:
    """workflow_name -> ordered list of script paths"""
    try:
        return json.loads(_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict[str, list[str]]):
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2))


def list_workflows() -> list[str]:
    return sorted(_load().keys())


def get_steps(name: str) -> list[str]:
    return _load().get(name, [])


def save_workflow(name: str, steps: list[str]):
    data = _load()
    data[name] = steps
    _save(data)


def delete_workflow(name: str):
    data = _load()
    data.pop(name, None)
    _save(data)
