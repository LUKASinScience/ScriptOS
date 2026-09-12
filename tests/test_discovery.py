from pathlib import Path

from app.core.tool import ParameterType
from app.discovery.python_parser import parse_python_script

FIXTURE = Path(__file__).parent / "fixtures" / "sample_script.py"


def test_parses_all_parameters():
    tool = parse_python_script(str(FIXTURE))
    names = {p.name: p for p in tool.parameters}
    assert set(names) == {"input", "threshold", "threads", "verbose", "output_dir"}


def test_types_and_defaults():
    tool = parse_python_script(str(FIXTURE))
    by_name = {p.name: p for p in tool.parameters}
    assert by_name["input"].param_type == ParameterType.FILE_IN
    assert by_name["input"].required is True
    assert by_name["threshold"].param_type == ParameterType.FLOAT
    assert by_name["threshold"].default == 0.05
    assert by_name["threads"].param_type == ParameterType.INT
    assert by_name["threads"].default == 4
    assert by_name["verbose"].param_type == ParameterType.BOOL
    assert by_name["output_dir"].param_type == ParameterType.DIRECTORY


def test_reads_module_docstring_as_description():
    tool = parse_python_script(str(Path(__file__).parent / "fixtures" / "analyze.py"))
    assert "CSV" in tool.description


def test_detects_non_stdlib_dependencies():
    tool = parse_python_script(str(FIXTURE))
    assert [d.name for d in tool.dependencies] == ["numpy"]


if __name__ == "__main__":
    test_parses_all_parameters()
    test_types_and_defaults()
    test_reads_module_docstring_as_description()
    test_detects_non_stdlib_dependencies()
    print("ok")
