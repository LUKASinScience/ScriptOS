from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class ParameterType(Enum):
    FILE_IN = "file_in"
    FILE_OUT = "file_out"
    DIRECTORY = "directory"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    CHOICE = "choice"
    STR = "str"
    STR_LONG = "str_long"


@dataclass
class Parameter:
    name: str
    flag: str
    param_type: ParameterType
    label: str
    description: str = ""
    required: bool = False
    default: Any = None
    min_value: float | None = None
    max_value: float | None = None
    choices: list[str] = field(default_factory=list)
    extensions: list[str] = field(default_factory=list)


@dataclass
class Dependency:
    name: str
    required_version: str | None = None
    pip_install: str = ""
    conda_install: str = ""
    uv_install: str = ""
    docs_url: str | None = None


@dataclass
class Tool:
    name: str
    script_path: str
    interpreter: Literal["python", "r", "bash", "custom"]
    parameters: list[Parameter]
    dependencies: list[Dependency] = field(default_factory=list)
    description: str = ""
    version: str = ""
    docs_url: str | None = None
    citation: str | None = None
    source: Literal["yaml", "argparse_auto", "manual"] = "manual"
