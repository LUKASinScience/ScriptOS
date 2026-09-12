from pathlib import Path

from app.execution.executor import run_tool


def test_memory_limit_kills_runaway_script(tmp_path):
    result = run_tool(
        "memhog", ["python3", "tests/fixtures/memory_hog.py"], tmp_path, max_memory_mb=50,
    )
    assert result.exit_code != 0


def test_no_limits_means_unrestricted(tmp_path):
    result = run_tool(
        "analyze", ["python3", "tests/fixtures/analyze.py", "--input", "tests/fixtures/samples.csv"], tmp_path,
    )
    assert result.exit_code == 0


if __name__ == "__main__":
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        test_memory_limit_kills_runaway_script(Path(d))
        test_no_limits_means_unrestricted(Path(d))
    print("ok")
