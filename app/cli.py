"""scriptos: a small command-line companion for terminal-first workflows.

Everything here reuses the same environments and discovery logic as the GUI —
for people who'd rather activate an environment and work from a shell once
things are set up, without giving up ScriptOS's dependency/environment tracking.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from app.discovery.python_parser import parse_python_script
from app.discovery.r_parser import parse_r_script
from app.environments import assignments, dir_wallet, venv_manager
from app.execution.command_builder import interpreter_bin


def cmd_list(args):
    envs = venv_manager.list_envs()
    if not envs:
        print("No environments yet. Create one with: scriptos new <name>")
        return
    for name in envs:
        print(f"{name}  ({venv_manager.env_dir(name)})")
        for script in assignments.scripts_using_env(name):
            print(f"  - {script}")


def cmd_new(args):
    ok, error = venv_manager.create_env(args.name)
    print("Created." if ok else f"Failed: {error}", file=None if ok else sys.stderr)
    sys.exit(0 if ok else 1)


def cmd_dir_new(args):
    dir_wallet.add_dir(args.name, args.path)
    print(f"Saved '{args.name}' -> {dir_wallet.get_path(args.name)}")


def cmd_dir_list(args):
    dirs = dir_wallet.list_dirs()
    if not dirs:
        print("No saved directories yet. Add one with: scriptos dir new <name> <path>")
        return
    for name in dirs:
        print(f"{name}  ({dir_wallet.get_path(name)})")


def cmd_activate(args):
    if args.name not in venv_manager.list_envs():
        print(f"No such environment: {args.name}", file=sys.stderr)
        print("Run 'scriptos list' to see what's available.", file=sys.stderr)
        sys.exit(1)

    target_dir = None
    if args.dir:
        target_dir = dir_wallet.get_path(args.dir) or args.dir
        if not Path(target_dir).is_dir():
            print(f"No such directory (saved or literal path): {args.dir}", file=sys.stderr)
            sys.exit(1)

    bin_dir = venv_manager.env_python(args.name).parent
    os.environ["VIRTUAL_ENV"] = str(venv_manager.env_dir(args.name))
    os.environ["PATH"] = f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    os.environ.pop("PYTHONHOME", None)
    if target_dir:
        os.chdir(target_dir)

    shell = os.environ.get("SHELL", "/bin/bash")
    where = f" in {target_dir}" if target_dir else ""
    print(f"Activating '{args.name}'{where} — type 'exit' to leave this shell.")
    os.execvp(shell, [shell])  # replaces this process, same as `conda activate`/`poetry shell`


def cmd_run(args):
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Script not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    is_r = script_path.suffix.lower() == ".r"
    tool = (parse_r_script if is_r else parse_python_script)(str(script_path))
    interpreter = interpreter_bin(tool, args.env)
    command = [interpreter, str(script_path), *args.script_args]
    sys.exit(subprocess.run(command).returncode)


def main():
    parser = argparse.ArgumentParser(prog="scriptos", description="Command-line companion to the ScriptOS app.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List saved environments and which scripts use them.").set_defaults(func=cmd_list)

    p_new = sub.add_parser("new", help="Create a new environment.")
    p_new.add_argument("name")
    p_new.set_defaults(func=cmd_new)

    p_activate = sub.add_parser("activate", help="Open a subshell with an environment active on PATH.")
    p_activate.add_argument("name")
    p_activate.add_argument("--dir", default=None, help="Saved directory name (or a literal path) to cd into first")
    p_activate.set_defaults(func=cmd_activate)

    p_dir = sub.add_parser("dir", help="Manage saved directories (the directory wallet).")
    dir_sub = p_dir.add_subparsers(dest="dir_command", required=True)
    p_dir_new = dir_sub.add_parser("new", help="Save a directory under a name.")
    p_dir_new.add_argument("name")
    p_dir_new.add_argument("path")
    p_dir_new.set_defaults(func=cmd_dir_new)
    dir_sub.add_parser("list", help="List saved directories.").set_defaults(func=cmd_dir_list)

    p_run = sub.add_parser("run", help="Run a script directly, optionally inside a saved environment.")
    p_run.add_argument("script")
    p_run.add_argument("--env", default=None, help="Environment name (default: system interpreter)")
    p_run.add_argument("script_args", nargs=argparse.REMAINDER)
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
