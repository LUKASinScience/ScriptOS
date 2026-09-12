from pathlib import Path

from app.core.tool import ParameterType
from app.discovery.r_parser import parse_r_script

FIXTURE = Path(__file__).parent / "fixtures" / "sample_r_script.R"


def test_parses_all_options():
    tool = parse_r_script(str(FIXTURE))
    assert tool.interpreter == "r"
    names = {p.name for p in tool.parameters}
    assert names == {"input", "threshold", "output_dir", "verbose"}


def test_types_and_defaults():
    tool = parse_r_script(str(FIXTURE))
    by_name = {p.name: p for p in tool.parameters}
    assert by_name["input"].param_type == ParameterType.FILE_IN
    assert by_name["input"].required is True
    assert by_name["threshold"].param_type == ParameterType.FLOAT
    assert by_name["threshold"].default == "0.05"
    assert by_name["output_dir"].param_type == ParameterType.DIRECTORY
    assert by_name["verbose"].param_type == ParameterType.BOOL


def test_detects_non_base_dependencies():
    tool = parse_r_script(str(FIXTURE))
    assert [d.name for d in tool.dependencies] == ["DESeq2"]


def test_runnable_script_has_no_extra_dependencies():
    tool = parse_r_script(str(Path(__file__).parent / "fixtures" / "runnable_r_tool.R"))
    assert tool.dependencies == []
    assert "threshold" in tool.description


if __name__ == "__main__":
    test_parses_all_options()
    test_types_and_defaults()
    test_detects_non_base_dependencies()
    test_runnable_script_has_no_extra_dependencies()
    print("ok")
