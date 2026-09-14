# Changelog

## Unreleased

- Static risk scan for Python scripts (flags `eval`, `os.system`, `pickle.loads`, etc.) shown on the analysis card
- Optional memory/CPU limits that auto-kill a runaway run
- Light mode is now the default theme (dark still selectable, takes effect after restart)
- Power Terminal now brings the opened Terminal.app window to the foreground
- GitHub Actions release pipeline: pushing a `v*` tag builds `ScriptOS.dmg` (macOS) and `ScriptOS-windows.zip` (Windows) and attaches them to a GitHub Release
- MIT license

## 0.1.0

- Initial release: script discovery (Python/R), auto-generated forms, environments, secrets wallet, workflows, CLI + Power Terminal
