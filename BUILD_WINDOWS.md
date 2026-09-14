# Building ScriptOS for Windows

Most people don't need this — download `ScriptOS-windows.zip` from
**[Releases](../../releases/latest)**, unzip, and run `ScriptOS.exe`. It's
built automatically by `.github/workflows/release.yml` on every tagged
release.

This doc is only for building a copy yourself. PyInstaller doesn't
cross-compile — a Windows `.exe` can only be built by actually running
PyInstaller on Windows. Two ways:

## Option A: GitHub Actions (no Windows machine needed)

1. Push this repo to GitHub (or push a tag like `v0.1.0`).
2. Go to **Actions → Release → Run workflow** (or just push a `v*` tag).
3. Download the `ScriptOS-windows.zip` artifact when it finishes.

## Option B: On an actual Windows machine

```bat
build_windows.bat
```

This creates a venv, installs dependencies, and runs PyInstaller with the
Windows icon (`app_icon.ico`). Output: `dist\ScriptOS\ScriptOS.exe`.

## Packaging as a proper installer (optional, either option)

The raw `dist/ScriptOS/` folder runs fine as-is (zip it and tell people to
unzip + run the `.exe`). For a real installer with a Start Menu entry and
uninstaller, wrap it with [Inno Setup](https://jrsoftware.org/isinfo.php)
(free, Windows-only, not something we can run from here) — point it at
`dist/ScriptOS/` as the source folder.
