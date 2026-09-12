#!/bin/bash
# Builds a standalone ScriptOS.app (or .exe on Windows) — no Python/venv needed to run it.
set -e
cd "$(dirname "$0")"
.venv/bin/pyinstaller --windowed --name ScriptOS --icon app_icon.icns --noconfirm app/main.py
echo "Built: dist/ScriptOS.app (or dist/ScriptOS/ScriptOS.exe on Windows)"
