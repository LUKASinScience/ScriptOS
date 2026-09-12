"""Workflows: chain scripts sequentially, each step's declared output location
auto-wired into the next step's first file/directory input. Deliberately not a
full pipeline engine — no branching, no conditions, one linear chain."""
import html
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.gui.icons import lucide_icon
from app.gui.theme import COLORS
from app.gui.workers import WorkflowRunner
from app.workflows import storage as workflow_storage


class WorkflowsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._workflow_steps: list[str] = []
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        header = QHBoxLayout()
        back_btn = QPushButton(" Back")
        back_btn.setObjectName("linkButton")
        back_btn.setIcon(lucide_icon("arrow-left", color=COLORS["text_dim"]))
        back_btn.clicked.connect(self.window.leave_workflows)
        title = QLabel("Workflows")
        title.setObjectName("heading")
        header.addWidget(back_btn)
        header.addWidget(title)
        header.addStretch()
        outer.addLayout(header)

        hint = QLabel(
            "A workflow runs a fixed sequence of scripts, one after another. Each step's declared "
            "output location is fed into the next step's first file/directory input automatically. "
            "This is a simple chain, not a full pipeline engine — no branching, no conditions."
        )
        hint.setWordWrap(True)
        outer.addWidget(hint)

        columns = QHBoxLayout()
        columns.setSpacing(16)
        outer.addLayout(columns, stretch=1)

        # --- saved workflows ---
        wf_col = QVBoxLayout()
        wf_col.addWidget(QLabel("SAVED WORKFLOWS"))
        self.workflow_list = QListWidget()
        self.workflow_list.currentItemChanged.connect(self._render_workflow_detail)
        wf_col.addWidget(self.workflow_list, stretch=1)
        wf_btn_row = QHBoxLayout()
        new_wf_btn = QPushButton(" New workflow")
        new_wf_btn.setIcon(lucide_icon("file-input", color=COLORS["text"]))
        new_wf_btn.clicked.connect(self._new_workflow)
        delete_wf_btn = QPushButton("Delete")
        delete_wf_btn.clicked.connect(self._delete_workflow)
        wf_btn_row.addWidget(new_wf_btn)
        wf_btn_row.addWidget(delete_wf_btn)
        wf_col.addLayout(wf_btn_row)
        columns.addLayout(wf_col, stretch=1)

        # --- steps for the selected workflow ---
        steps_col = QVBoxLayout()
        steps_col.addWidget(QLabel("STEPS (in order)"))
        self.workflow_steps_list = QListWidget()
        steps_col.addWidget(self.workflow_steps_list, stretch=1)
        step_btn_row = QHBoxLayout()
        add_step_btn = QPushButton(" Add step")
        add_step_btn.setIcon(lucide_icon("file-input", color=COLORS["text"]))
        add_step_btn.clicked.connect(self._add_workflow_step)
        remove_step_btn = QPushButton("Remove step")
        remove_step_btn.clicked.connect(self._remove_workflow_step)
        step_btn_row.addWidget(add_step_btn)
        step_btn_row.addWidget(remove_step_btn)
        steps_col.addLayout(step_btn_row)

        self.run_workflow_btn = QPushButton(" Run workflow")
        self.run_workflow_btn.setObjectName("primary")
        self.run_workflow_btn.setIcon(lucide_icon("play", color=COLORS["primary_text"]))
        self.run_workflow_btn.clicked.connect(self._run_workflow)
        self.run_workflow_btn.setEnabled(False)
        steps_col.addWidget(self.run_workflow_btn)

        self.workflow_log = QPlainTextEdit()
        self.workflow_log.setReadOnly(True)
        self.workflow_log.setPlaceholderText("Workflow output appears here…")
        steps_col.addWidget(self.workflow_log, stretch=1)

        columns.addLayout(steps_col, stretch=1)

    def refresh(self):
        self.workflow_list.clear()
        for name in workflow_storage.list_workflows():
            self.workflow_list.addItem(name)
        self.workflow_steps_list.clear()
        self._workflow_steps = []
        self.run_workflow_btn.setEnabled(False)

    def _render_workflow_detail(self, current: QListWidgetItem | None, _previous=None):
        self.workflow_steps_list.clear()
        if not current:
            self._workflow_steps = []
            self.run_workflow_btn.setEnabled(False)
            return
        self._workflow_steps = workflow_storage.get_steps(current.text())
        for step in self._workflow_steps:
            self.workflow_steps_list.addItem(Path(step).name)
        self.run_workflow_btn.setEnabled(len(self._workflow_steps) >= 1)

    def _new_workflow(self):
        name, ok = QInputDialog.getText(self, "New workflow", "Name (e.g. 'Preprocess then analyze'):")
        if not ok or not name.strip():
            return
        workflow_storage.save_workflow(name.strip(), [])
        self.refresh()

    def _delete_workflow(self):
        item = self.workflow_list.currentItem()
        if not item:
            return
        workflow_storage.delete_workflow(item.text())
        self.refresh()

    def _add_workflow_step(self):
        item = self.workflow_list.currentItem()
        if not item:
            QMessageBox.information(self, "No workflow selected", "Create or select a workflow first.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Add step", "", "Scripts (*.py *.R)")
        if not path:
            return
        self._workflow_steps.append(path)
        workflow_storage.save_workflow(item.text(), self._workflow_steps)
        self._render_workflow_detail(item)

    def _remove_workflow_step(self):
        item = self.workflow_list.currentItem()
        row = self.workflow_steps_list.currentRow()
        if not item or row < 0:
            return
        del self._workflow_steps[row]
        workflow_storage.save_workflow(item.text(), self._workflow_steps)
        self._render_workflow_detail(item)

    def _run_workflow(self):
        if not self._workflow_steps:
            return
        self.workflow_log.clear()
        self.run_workflow_btn.setEnabled(False)
        self.run_workflow_btn.setText(" Running…")
        self._workflow_runner = WorkflowRunner(list(self._workflow_steps))
        self._workflow_runner.line_received.connect(self._append_workflow_log)
        self._workflow_runner.finished_workflow.connect(self._on_workflow_finished)
        self._workflow_runner.start()

    def _append_workflow_log(self, stream: str, text: str):
        color = COLORS["danger"] if stream == "stderr" else COLORS["text_dim"]
        self.workflow_log.appendHtml(f'<span style="color:{color}">{html.escape(text)}</span>')

    def _on_workflow_finished(self, ok: bool):
        self.workflow_log.appendHtml(f"<b>{'✓ Workflow succeeded' if ok else '✗ Workflow failed'}</b>")
        self.run_workflow_btn.setEnabled(True)
        self.run_workflow_btn.setText(" Run workflow")
