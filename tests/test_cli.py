import subprocess
import sys

from app.environments import dir_wallet, venv_manager

_TEST_ENV = "cli_test_env_tmp"
_TEST_DIR_NAME = "cli_test_dir_tmp"


def test_run_subcommand_executes_script():
    result = subprocess.run(
        [sys.executable, "-m", "app.cli", "run", "tests/fixtures/analyze.py",
         "--", "--input", "tests/fixtures/samples.csv"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Done." in result.stdout


def test_new_and_list_roundtrip():
    venv_manager.delete_env(_TEST_ENV)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.cli", "new", _TEST_ENV],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert _TEST_ENV in venv_manager.list_envs()

        result = subprocess.run(
            [sys.executable, "-m", "app.cli", "list"], capture_output=True, text=True,
        )
        assert _TEST_ENV in result.stdout
    finally:
        venv_manager.delete_env(_TEST_ENV)


def test_dir_new_and_list_roundtrip():
    dir_wallet.delete_dir(_TEST_DIR_NAME)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "app.cli", "dir", "new", _TEST_DIR_NAME, "tests/fixtures"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert dir_wallet.get_path(_TEST_DIR_NAME).endswith("tests/fixtures")

        result = subprocess.run(
            [sys.executable, "-m", "app.cli", "dir", "list"], capture_output=True, text=True,
        )
        assert _TEST_DIR_NAME in result.stdout
    finally:
        dir_wallet.delete_dir(_TEST_DIR_NAME)


if __name__ == "__main__":
    test_run_subcommand_executes_script()
    test_new_and_list_roundtrip()
    test_dir_new_and_list_roundtrip()
    print("ok")
