"""The only place a script gets loaded: drop zone, browse button, recent list."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from app.gui.icons import lucide_icon
from app.gui.theme import COLORS
from app.storage.recent_tools import load_recent


class EmptyStatePage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.addStretch()

        title = QLabel("ScriptOS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel("Turn a Python or R script into a form. No terminal required.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 13px;")
        layout.addWidget(subtitle)
        layout.addSpacing(28)

        zone = QLabel()
        zone.setObjectName("dropzone")
        zone.setMinimumHeight(200)

        zone_inner = QVBoxLayout(zone)
        zone_inner.addStretch()
        icon_holder = QLabel()
        icon_holder.setPixmap(lucide_icon("cloud-upload", color=COLORS["text_dim"], size=32).pixmap(32, 32))
        icon_holder.setAlignment(Qt.AlignCenter)
        icon_holder.setStyleSheet("border: none; background: transparent;")
        zone_inner.addWidget(icon_holder)
        zone_inner.addSpacing(10)
        text = QLabel("Drag & drop a Python (.py) or R (.R) script here")
        text.setAlignment(Qt.AlignCenter)
        text.setStyleSheet(f"color: {COLORS['text_dim']}; border: none; background: transparent;")
        zone_inner.addWidget(text)
        zone_inner.addStretch()
        layout.addWidget(zone)

        browse_row = QHBoxLayout()
        browse_row.addStretch()
        browse_btn = QPushButton(" Browse for a script")
        browse_btn.setObjectName("primary")
        browse_btn.setIcon(lucide_icon("file-input", color=COLORS["primary_text"]))
        browse_btn.clicked.connect(self.window.load_script)
        browse_row.addWidget(browse_btn)
        browse_row.addStretch()
        layout.addSpacing(20)
        layout.addLayout(browse_row)
        layout.addSpacing(24)

        self.recent_label = QLabel("RECENT")
        self.recent_label.setObjectName("sectionLabel")
        self.recent_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.recent_label)
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(140)
        self.recent_list.itemClicked.connect(self._open_recent_item)
        layout.addWidget(self.recent_list)

        layout.addStretch()

    def refresh(self):
        entries = [e for e in load_recent() if Path(e["path"]).exists()]
        self.recent_list.clear()
        for entry in entries:
            item = QListWidgetItem(f"{entry['name']}  —  {entry['path']}")
            item.setData(Qt.UserRole, entry["path"])
            self.recent_list.addItem(item)
        has_recent = bool(entries)
        self.recent_label.setVisible(has_recent)
        self.recent_list.setVisible(has_recent)

    def _open_recent_item(self, item: QListWidgetItem):
        self.window.open_script(item.data(Qt.UserRole))
