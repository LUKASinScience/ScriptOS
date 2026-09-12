@echo off
REM Builds ScriptOS.exe on Windows. Must run ON Windows — PyInstaller does not
REM cross-compile, so this cannot be produced from macOS/Linux.
setlocal

python -m venv .venv
.venv\Scripts\pip install -q PySide6 cryptography psutil pyinstaller -e .
.venv\Scripts\pyinstaller --windowed --name ScriptOS --icon app_icon.ico --noconfirm app\main.py

echo Built: dist\ScriptOS\ScriptOS.exe
