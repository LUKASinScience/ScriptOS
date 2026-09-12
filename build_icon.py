"""Renders the ScriptOS app icon (rounded square, accent color, play glyph) at every
size macOS needs, then builds a .icns via the built-in `iconutil`. Re-run this if the
icon design ever changes — app_icon.icns and docs/assets/logo.png are its output."""
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

BG = "#5B9EE8"
GLYPH = "#14120F"
PLAY_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    f'stroke="{GLYPH}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z" '
    f'fill="{GLYPH}"/></svg>'
)

ICONSET = Path("build_icon.iconset")
SIZES = [16, 32, 64, 128, 256, 512, 1024]


def render(size: int) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    path = QPainterPath()
    radius = size * 0.22
    path.addRoundedRect(QRectF(0, 0, size, size), radius, radius)
    painter.fillPath(path, QBrush(QColor(BG)))

    renderer = QSvgRenderer(PLAY_SVG.encode())
    margin = size * 0.28
    renderer.render(painter, QRectF(margin, margin, size - 2 * margin, size - 2 * margin))
    painter.end()
    return pixmap


def main():
    app = QApplication(sys.argv)
    ICONSET.mkdir(exist_ok=True)
    for size in SIZES:
        render(size).save(str(ICONSET / f"icon_{size}x{size}.png"))
        if size <= 512:
            render(size * 2).save(str(ICONSET / f"icon_{size}x{size}@2x.png"))
    subprocess.run(["iconutil", "-c", "icns", str(ICONSET), "-o", "app_icon.icns"], check=True)
    render(512).save("docs/assets/logo.png")
    # ponytail: single 256x256 frame, not a proper multi-resolution .ico — fine for
    # modern Windows, upgrade to multi-size if it ever looks rough at small sizes.
    render(256).save("app_icon.ico", "ico")
    print("Wrote app_icon.icns, app_icon.ico, and docs/assets/logo.png")


if __name__ == "__main__":
    main()
