"""Color tokens and Qt stylesheet — single source of truth. A theme switch
takes effect on next launch (icons and per-widget stylesheets are baked in at
construction time, so a live re-theme would mean rebuilding every widget —
not worth the complexity for a rarely-toggled setting).
"""
import json
from pathlib import Path

_PREF_PATH = Path.home() / ".scriptos" / "settings.json"

# Warm dark neutrals (slight brown/grey tint instead of blue-black) with a single cool
# accent for contrast — same technique Linear/Obsidian use for a calmer, less "cold" dark UI.
COLORS_DARK = {
    "bg": "#1B1917",
    "panel": "#242220",
    "card": "#242220",
    "border": "#39352F",
    "border_strong": "#4A443D",
    "text": "#EDEAE5",
    "text_dim": "#A8A199",
    "accent": "#5B9EE8",
    "danger": "#E2685C",
    "warning": "#E0A855",
    "success": "#6CB98A",
    "primary_text": "#14120F",
    "primary_hover": "#6FADF0",
    "hover_bg": "#2A2724",
    "console_bg": "#141210",
}

# Same warm-neutral language, inverted: off-white instead of near-black, a
# slightly deeper accent so it still contrasts against a light background.
COLORS_LIGHT = {
    "bg": "#FAF8F4",
    "panel": "#FFFFFF",
    "card": "#FFFFFF",
    "border": "#E5DFD3",
    "border_strong": "#D0C6B4",
    "text": "#1E1B16",
    "text_dim": "#6B6255",
    "accent": "#3E7DD8",
    "danger": "#C94A3D",
    "warning": "#B8791E",
    "success": "#2F8F5B",
    "primary_text": "#FFFFFF",
    "primary_hover": "#5A94E4",
    "hover_bg": "#F1EBDF",
    "console_bg": "#F3EFE6",
}


def load_theme_name() -> str:
    try:
        return json.loads(_PREF_PATH.read_text()).get("theme", "light")
    except (OSError, json.JSONDecodeError):
        return "light"


def save_theme_name(name: str):
    _PREF_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREF_PATH.write_text(json.dumps({"theme": name}, indent=2))


def build_stylesheet(colors: dict) -> str:
    return f"""
QMainWindow, QWidget {{ background: {colors['bg']}; color: {colors['text']}; font-size: 13px; }}
QLineEdit {{ background: {colors['panel']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 8px 10px; selection-background-color: {colors['accent']}; }}
QLineEdit:focus {{ border: 1px solid {colors['accent']}; }}
QPushButton {{ background: {colors['panel']}; color: {colors['text']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 8px 16px; font-weight: 500; }}
QPushButton:hover {{ border-color: {colors['border_strong']}; background: {colors['hover_bg']}; }}
QPushButton:disabled {{ background: {colors['panel']}; color: {colors['text_dim']}; border-color: {colors['border']}; }}
QPushButton#primary {{ background: {colors['accent']}; color: {colors['primary_text']}; border: none; font-weight: 600; padding: 11px 20px; }}
QPushButton#primary:hover {{ background: {colors['primary_hover']}; }}
QPushButton#primary:disabled {{ background: {colors['border']}; color: {colors['text_dim']}; }}
QPushButton#ghostIcon {{ background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 6px 9px; }}
QPushButton#ghostIcon:hover {{ border-color: {colors['border']}; background: {colors['panel']}; }}
QPushButton#linkButton {{ background: transparent; border: none; color: {colors['text_dim']}; padding: 4px 6px; font-weight: 500; }}
QPushButton#linkButton:hover {{ color: {colors['accent']}; }}
QPlainTextEdit {{ background: {colors['console_bg']}; color: {colors['text_dim']}; border: 1px solid {colors['border']}; font-family: 'JetBrains Mono', monospace; border-radius: 8px; padding: 8px; }}
QListWidget {{ background: {colors['console_bg']}; color: {colors['text']}; border: 1px solid {colors['border']}; border-radius: 8px; padding: 4px; }}
QListWidget::item {{ padding: 6px 4px; border-radius: 4px; }}
QListWidget::item:hover {{ background: {colors['panel']}; }}
QTabWidget::pane {{ border: 1px solid {colors['border']}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {colors['text_dim']}; padding: 6px 14px; border: none; }}
QTabBar::tab:selected {{ color: {colors['text']}; border-bottom: 2px solid {colors['accent']}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {colors['border_strong']}; border-radius: 5px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {colors['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QComboBox {{ background: {colors['panel']}; color: {colors['text']}; border: 1px solid {colors['border']}; border-radius: 6px; padding: 5px 8px; }}
QComboBox:hover {{ border-color: {colors['border_strong']}; }}
QComboBox QAbstractItemView {{ background: {colors['panel']}; color: {colors['text']}; border: 1px solid {colors['border']}; selection-background-color: {colors['accent']}; }}
QLabel {{ color: {colors['text_dim']}; }}
QLabel#heading {{ color: {colors['text']}; font-size: 16px; font-weight: 600; }}
QLabel#dropzone {{ border: 2px dashed {colors['border']}; border-radius: 14px; color: {colors['text_dim']}; font-size: 14px; }}
QWidget#card {{ background: {colors['card']}; border: 1px solid {colors['border']}; border-radius: 10px; }}
QLabel#sectionLabel {{ color: {colors['text_dim']}; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }}
"""


THEME_NAME = load_theme_name()
COLORS = COLORS_LIGHT if THEME_NAME == "light" else COLORS_DARK
STYLESHEET = build_stylesheet(COLORS)
