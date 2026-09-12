"""Renders a real screenshot of ScriptOS (via QWidget.grab — no OS screen-recording
permission needed, since it paints the widget tree directly) and composites it into
a simple MacBook frame for the docs guide. Re-run after any UI change."""
import sys

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication

from app.gui.app_window import AppWindow

SCREEN_W, SCREEN_H = 1280, 800  # matches the app's recommended window size
BEZEL = 52
HINGE_H = 44
BASE_H = 32
CORNER = 28


def capture_app() -> QPixmap:
    window = AppWindow()
    window.resize(SCREEN_W, SCREEN_H)
    window.show()

    app = QApplication.instance()
    for _ in range(10):
        app.processEvents()

    window._load_path("tests/fixtures/plot_histogram.py")
    for _ in range(10):
        app.processEvents()
    window.inputs["input"].setText("tests/fixtures/samples.csv")
    window._refresh()
    for _ in range(10):
        app.processEvents()

    pixmap = window.grab()
    pixmap.setDevicePixelRatio(1.0)  # treat as a plain bitmap so frame math uses real pixel counts
    window.close()
    return pixmap


def build_macbook_mockup(screenshot: QPixmap) -> QPixmap:
    screen_w, screen_h = screenshot.width(), screenshot.height()
    pad = 40
    lid_w = screen_w + BEZEL * 2
    lid_h = screen_h + BEZEL * 2
    total_w = lid_w + pad * 2
    total_h = lid_h + HINGE_H + BASE_H + pad * 2

    canvas = QPixmap(total_w, total_h)
    canvas.fill(Qt.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)

    ox, oy = pad, pad

    # lid (aluminum body) with a subtle vertical gradient
    lid_rect = QRectF(ox, oy, lid_w, lid_h)
    lid_path = QPainterPath()
    lid_path.addRoundedRect(lid_rect, CORNER, CORNER)
    gradient = QLinearGradient(0, oy, 0, oy + lid_h)
    gradient.setColorAt(0, QColor("#4a4a4e"))
    gradient.setColorAt(1, QColor("#2c2c2f"))
    painter.fillPath(lid_path, QBrush(gradient))

    # screen (bezel is the visible aluminum border, this is the black inset + content)
    screen_rect = QRectF(ox + BEZEL, oy + BEZEL, screen_w, screen_h)
    screen_path = QPainterPath()
    screen_path.addRoundedRect(screen_rect, 8, 8)
    painter.setClipPath(screen_path)
    painter.drawPixmap(QPoint(ox + BEZEL, oy + BEZEL), screenshot)
    painter.setClipping(False)

    # camera notch
    painter.setBrush(QColor("#111"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QPoint(int(ox + lid_w / 2), int(oy + BEZEL / 2)), 6, 6)

    # hinge
    hinge_rect = QRectF(ox + 40, oy + lid_h, lid_w - 80, HINGE_H)
    painter.setBrush(QColor("#1c1c1e"))
    painter.drawRect(hinge_rect)

    # base (keyboard deck edge, wider than the lid, trapezoid-ish via rounded rect)
    base_w = lid_w + 60
    base_rect = QRectF(ox - 30, oy + lid_h + HINGE_H, base_w, BASE_H)
    base_path = QPainterPath()
    base_path.addRoundedRect(base_rect, 10, 10)
    base_gradient = QLinearGradient(0, base_rect.top(), 0, base_rect.bottom())
    base_gradient.setColorAt(0, QColor("#5a5a5e"))
    base_gradient.setColorAt(1, QColor("#38383b"))
    painter.fillPath(base_path, QBrush(base_gradient))

    painter.end()
    return canvas


def main():
    app = QApplication(sys.argv)
    screenshot = capture_app()
    screenshot.save("docs/assets/screenshot.png")
    mockup = build_macbook_mockup(screenshot)
    mockup.save("docs/assets/macbook-mockup.png")
    print(f"Wrote docs/assets/screenshot.png ({screenshot.width()}x{screenshot.height()})")
    print(f"Wrote docs/assets/macbook-mockup.png ({mockup.width()}x{mockup.height()})")


if __name__ == "__main__":
    main()
