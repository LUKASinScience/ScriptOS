"""A QLineEdit that accepts drag & drop of a file/folder path and pairs with a Browse button."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from app.core.tool import ParameterType
from app.gui.icons import lucide_icon

_TRUE_STRINGS = {"true", "1", "yes", "on"}


class BoolField(QCheckBox):
    """Checkbox with the text()/setText() interface the form code uses for every field type."""

    def text(self) -> str:
        return "true" if self.isChecked() else ""

    def setText(self, value):
        self.setChecked(str(value).strip().lower() in _TRUE_STRINGS)

    @property
    def textChanged(self):
        return self.stateChanged


class DropLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.setText(urls[0].toLocalFile())


class FileField(QWidget):
    """Text field + Browse button, drag & drop enabled, dialog mode depends on ParameterType."""

    def __init__(self, param_type: ParameterType, extensions: list[str] | None = None, enable_dnd: bool = True, parent=None):
        super().__init__(parent)
        self.param_type = param_type
        self.extensions = extensions or []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if enable_dnd:
            self.edit = DropLineEdit()
            self.edit.setPlaceholderText("Drop a file here or browse…")
        else:
            self.edit = QLineEdit()
            self.edit.setPlaceholderText("Browse…")
        browse = QPushButton()
        browse.setObjectName("ghostIcon")
        browse.setIcon(lucide_icon("folder-open", color="#A0A0B0"))
        browse.setToolTip("Browse…")
        browse.setCursor(Qt.PointingHandCursor)
        browse.clicked.connect(self._browse)
        layout.addWidget(self.edit, stretch=1)
        layout.addWidget(browse)

    def _browse(self):
        if self.param_type == ParameterType.FILE_IN:
            filt = f"({' '.join('*.' + e for e in self.extensions)})" if self.extensions else "All files (*)"
            path, _ = QFileDialog.getOpenFileName(self, "Select input file", "", filt)
        elif self.param_type == ParameterType.FILE_OUT:
            path, _ = QFileDialog.getSaveFileName(self, "Select output file")
        else:
            path = QFileDialog.getExistingDirectory(self, "Select directory")
        if path:
            self.edit.setText(path)

    def text(self) -> str:
        return self.edit.text()

    def setText(self, value: str):
        self.edit.setText(value)

    @property
    def textChanged(self):
        return self.edit.textChanged
