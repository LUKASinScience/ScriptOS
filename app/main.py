import os
import sys

from PySide6.QtWidgets import QApplication

from app.gui.app_window import AppWindow

# GUI-launched macOS apps (Finder/Dock) get a minimal PATH that skips Homebrew —
# interpreters installed via `brew install` are invisible to shutil.which()/subprocess
# without this, even though they work fine from a terminal.
_EXTRA_PATH_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")


def _augment_path():
    dirs = os.environ.get("PATH", "").split(os.pathsep)
    for d in _EXTRA_PATH_DIRS:
        if d not in dirs:
            dirs.append(d)
    os.environ["PATH"] = os.pathsep.join(dirs)


def main():
    _augment_path()
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
