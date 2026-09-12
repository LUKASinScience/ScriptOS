"""The main working page: script analysis, auto-generated parameter form,
run controls, and the Logs/Files/Report/History output tabs. Only shown once
a script is loaded."""
import html
import json
import shlex
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.tool import Parameter, ParameterType, Tool
from app.discovery.file_heuristics import is_output_param
from app.discovery.python_parser import parse_python_script
from app.discovery.r_parser import parse_r_script
from app.discovery.risk_scan import scan_risks
from app.environments import assignments, credentials, venv_manager
from app.execution.command_builder import build_command, interpreter_bin
from app.gui.components.file_field import BoolField, FileField
from app.gui.flow_layout import FlowLayout
from app.gui.icons import lucide_icon
from app.gui.theme import COLORS
from app.gui.workers import InstallWorker, RunWorker
from app.storage.recent_tools import add_recent
from app.validation.dependency_checker import check_dependencies, check_interpreter
from app.validation.validators import is_runnable, validate_all

_SYSTEM_PYTHON_LABEL = "System Python"
_NO_CREDENTIALS_LABEL = "None"

_INPUT_FILE_TYPES = {ParameterType.FILE_IN, ParameterType.DIRECTORY}
_INTERACTIVE_MARKERS = {"python": "input(", "r": "readline("}


def _find_output_param(tool: Tool) -> Parameter | None:
    """The script's own parameter that points at where it writes results, if it has one."""
    for param in tool.parameters:
        if param.param_type in (ParameterType.FILE_OUT, ParameterType.DIRECTORY) and is_output_param(param.name):
            return param
    return None


def _uses_interactive_input(tool: Tool) -> bool:
    """Best-effort text scan: a script that reads from the terminal will fail fast
    (stdin is closed for runs) rather than hang, but it's worth flagging up front."""
    marker = _INTERACTIVE_MARKERS.get(tool.interpreter)
    if not marker:
        return False
    try:
        return marker in Path(tool.script_path).read_text()
    except OSError:
        return False


class WorkspacePage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window

        self.tool: Tool | None = None
        self.inputs: dict[str, QWidget] = {}
        self.worker: RunWorker | None = None
        self._interpreter_ok = True
        self._custom_runs_dir: str | None = None
        self._selected_env: str | None = None
        self._selected_credential_set: str | None = None
        self._missing_deps: list[str] = []

        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        top_bar = QHBoxLayout()
        self.tool_label = QLabel("")
        self.tool_label.setObjectName("heading")
        change_btn = QPushButton(" Change script")
        change_btn.setObjectName("linkButton")
        change_btn.setIcon(lucide_icon("file-input", color=COLORS["text_dim"]))
        change_btn.clicked.connect(self.window.go_to_empty_state)
        top_bar.addWidget(self.tool_label)
        top_bar.addStretch()
        top_bar.addWidget(change_btn)
        outer.addLayout(top_bar)

        # everything configuration-related scrolls; Run/Stop and the output tabs below stay fixed
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(14)
        scroll.setWidget(scroll_content)
        outer.addWidget(scroll, stretch=2)

        self.analysis_card = QLabel("")
        self.analysis_card.setObjectName("card")
        self.analysis_card.setWordWrap(True)
        self.analysis_card.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(self.analysis_card)

        self.create_env_btn = QPushButton(" Create environment for this script")
        self.create_env_btn.setObjectName("primary")
        self.create_env_btn.setIcon(lucide_icon("folder-open", color=COLORS["primary_text"]))
        self.create_env_btn.clicked.connect(self._create_env_for_script)
        self.create_env_btn.hide()
        layout.addWidget(self.create_env_btn)

        self.install_missing_btn = QPushButton(" Install missing dependencies into this environment")
        self.install_missing_btn.setIcon(lucide_icon("cloud-upload", color=COLORS["text"]))
        self.install_missing_btn.clicked.connect(self._install_missing_deps)
        self.install_missing_btn.hide()
        layout.addWidget(self.install_missing_btn)

        run_settings_row = QHBoxLayout()
        run_settings_row.addWidget(QLabel("Environment:"))
        self.env_combo = QComboBox()
        self.env_combo.currentTextChanged.connect(self._on_env_selected)
        run_settings_row.addWidget(self.env_combo, stretch=1)
        run_settings_row.addWidget(QLabel("Secrets:"))
        self.cred_combo = QComboBox()
        self.cred_combo.currentTextChanged.connect(self._on_cred_selected)
        run_settings_row.addWidget(self.cred_combo, stretch=1)
        layout.addLayout(run_settings_row)

        params_label = QLabel("PARAMETERS")
        params_label.setObjectName("sectionLabel")
        layout.addWidget(params_label)

        self.form_container = QWidget()
        self.form_layout = FlowLayout(self.form_container, h_spacing=12, v_spacing=12)
        layout.addWidget(self.form_container)

        output_location_row = QHBoxLayout()
        output_icon = QLabel()
        output_icon.setPixmap(lucide_icon("folder-open", color=COLORS["text_dim"], size=15).pixmap(15, 15))
        self.output_location_label = QLabel("")
        self.output_location_label.setWordWrap(True)
        self.output_location_edit_btn = QPushButton()
        self.output_location_edit_btn.setObjectName("ghostIcon")
        self.output_location_edit_btn.setIcon(lucide_icon("folder-open", color=COLORS["text_dim"]))
        self.output_location_edit_btn.setToolTip("Change where results are saved")
        self.output_location_edit_btn.clicked.connect(self._change_output_location)
        output_location_row.addWidget(output_icon)
        output_location_row.addWidget(self.output_location_label, stretch=1)
        output_location_row.addWidget(self.output_location_edit_btn)
        layout.addLayout(output_location_row)

        self.command_preview = QLabel("")
        self.command_preview.setWordWrap(True)
        self.command_preview.setObjectName("card")
        self.command_preview.setContentsMargins(12, 10, 12, 10)
        self.command_preview.setStyleSheet(
            f"font-family: 'JetBrains Mono', monospace; color: {COLORS['text_dim']}; font-size: 12px;"
        )
        layout.addWidget(self.command_preview)

        self.validation_label = QLabel("")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)

        limits_row = QHBoxLayout()
        limits_row.addWidget(QLabel("Memory limit (MB):"))
        self.memory_limit_edit = QLineEdit()
        self.memory_limit_edit.setPlaceholderText("unlimited")
        self.memory_limit_edit.setFixedWidth(90)
        limits_row.addWidget(self.memory_limit_edit)
        limits_row.addWidget(QLabel("CPU limit (%):"))
        self.cpu_limit_edit = QLineEdit()
        self.cpu_limit_edit.setPlaceholderText("unlimited")
        self.cpu_limit_edit.setFixedWidth(90)
        limits_row.addWidget(self.cpu_limit_edit)
        limits_row.addStretch()
        layout.addLayout(limits_row)
        limits_hint = QLabel("Leave blank to run unrestricted. A safety net for runaway scripts, not a security sandbox.")
        limits_hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        layout.addWidget(limits_hint)
        layout.addStretch()

        self.run_btn = QPushButton(" Run")
        self.run_btn.setObjectName("primary")
        self.run_btn.setIcon(lucide_icon("play", color=COLORS["primary_text"]))
        self.run_btn.clicked.connect(self.run_tool)
        self.run_btn.setEnabled(False)
        outer.addWidget(self.run_btn)

        self.stop_btn = QPushButton(" Stop")
        self.stop_btn.setIcon(lucide_icon("square", color=COLORS["danger"]))
        self.stop_btn.clicked.connect(self.stop_run)
        self.stop_btn.hide()
        outer.addWidget(self.stop_btn)

        output_label = QLabel("OUTPUT")
        output_label.setObjectName("sectionLabel")
        outer.addWidget(output_label)

        self.output_tabs = QTabWidget()

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Output will appear here while the script runs…")
        self.output_tabs.addTab(self.log_view, "Logs")

        self.files_list = QListWidget()
        self.files_list.itemDoubleClicked.connect(self._open_file_item)
        self.output_tabs.addTab(self.files_list, "Files")

        self.report_view = QPlainTextEdit()
        self.report_view.setReadOnly(True)
        self.output_tabs.addTab(self.report_view, "Report")

        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._open_history_item)
        self.output_tabs.addTab(self.history_list, "History")

        outer.addWidget(self.output_tabs, stretch=1)

    # ---- loading a script ----

    def load_path(self, path: str):
        parser = parse_r_script if path.lower().endswith(".r") else parse_python_script
        self.tool = parser(path)
        self.tool_label.setText(self.tool.name)
        self._custom_runs_dir = None
        resolved_path = str(Path(path).resolve())
        assigned_env = assignments.get_assigned_env(resolved_path)
        self._selected_env = assigned_env if assigned_env in venv_manager.list_envs() else None
        assigned_creds = assignments.get_assigned_credentials(resolved_path)
        self._selected_credential_set = assigned_creds if assigned_creds in credentials.list_sets() else None
        add_recent(self.tool.name, resolved_path)
        self.window.refresh_recent_menu()
        self._populate_run_settings()
        self._render_analysis()
        self._render_form()
        self._refresh_history()

    def on_return_from_side_page(self):
        """Called when coming back from Environments/Workflows — env/credential
        lists may have changed, and the current tool's dropdowns should reflect it."""
        if not self.tool:
            return
        self._populate_run_settings()
        self._render_analysis()
        self._refresh()

    # ---- run history ----

    def _refresh_history(self):
        self.history_list.clear()
        runs_base = self._current_runs_base()
        if not runs_base.exists():
            return
        run_dirs = sorted((p for p in runs_base.iterdir() if p.is_dir()), reverse=True)
        for run_dir in run_dirs:
            info = {}
            command_json = run_dir / "command.json"
            if command_json.exists():
                try:
                    info = json.loads(command_json.read_text())
                except (OSError, json.JSONDecodeError):
                    pass
            exit_code = info.get("exit_code")
            duration = info.get("duration_seconds")
            if exit_code is None:
                status = "unfinished"
            elif exit_code == 0:
                status = "✓ success"
            else:
                status = f"✗ exit {exit_code}"
            duration_text = f", {duration:.1f}s" if duration is not None else ""
            label = f"{run_dir.name}  —  {status}{duration_text}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, str(run_dir))
            self.history_list.addItem(item)

    def _open_history_item(self, item: QListWidgetItem):
        run_dir = Path(item.data(Qt.UserRole))
        self._render_outputs(run_dir)
        command_json = run_dir / "command.json"
        try:
            info = json.loads(command_json.read_text())
        except (OSError, json.JSONDecodeError):
            info = {}
        lines = [
            f"Run: {run_dir.name}",
            f"Command: {shlex.join(info.get('command', []))}",
            f"Exit code: {info.get('exit_code', 'unknown')}",
            f"Duration: {info.get('duration_seconds', 'unknown')}s",
        ]
        self.report_view.setPlainText("\n".join(lines))
        self.output_tabs.setCurrentWidget(self.report_view)

    # ---- environment / credential selection ----

    def _populate_run_settings(self):
        self.env_combo.blockSignals(True)
        self.env_combo.clear()
        self.env_combo.addItem(_SYSTEM_PYTHON_LABEL)
        self.env_combo.addItems(venv_manager.list_envs())
        self.env_combo.setEnabled(self.tool.interpreter == "python")
        self.env_combo.setCurrentText(self._selected_env or _SYSTEM_PYTHON_LABEL)
        self.env_combo.blockSignals(False)

        self.cred_combo.blockSignals(True)
        self.cred_combo.clear()
        self.cred_combo.addItem(_NO_CREDENTIALS_LABEL)
        self.cred_combo.addItems(credentials.list_sets())
        self.cred_combo.setCurrentText(self._selected_credential_set or _NO_CREDENTIALS_LABEL)
        self.cred_combo.blockSignals(False)

    def _on_env_selected(self, text: str):
        self._selected_env = None if text == _SYSTEM_PYTHON_LABEL else text
        if self.tool:
            assignments.set_assigned_env(str(Path(self.tool.script_path).resolve()), self._selected_env)
        self._render_analysis()
        self._refresh()

    def _on_cred_selected(self, text: str):
        self._selected_credential_set = None if text == _NO_CREDENTIALS_LABEL else text
        if self.tool:
            assignments.set_assigned_credentials(str(Path(self.tool.script_path).resolve()), self._selected_credential_set)

    # ---- output location ----

    def _default_runs_dir(self) -> str:
        return str(Path(self.tool.script_path).parent / "runs")

    def _resolve_output_location(self) -> str:
        """Where results actually land: the script's own output parameter if it has
        one, otherwise ScriptOS's run bookkeeping folder (user-configurable)."""
        output_param = _find_output_param(self.tool)
        if output_param:
            field = self.inputs.get(output_param.name)
            return field.text() if field else ""
        return self._custom_runs_dir or self._default_runs_dir()

    def _change_output_location(self):
        path = QFileDialog.getExistingDirectory(self, "Choose where results are saved")
        if path:
            self._custom_runs_dir = path
            self._refresh()

    # ---- dependency / environment quick actions ----

    def _install_missing_deps(self):
        if not self._selected_env or not self._missing_deps:
            return
        self.install_missing_btn.setEnabled(False)
        self.install_missing_btn.setText(f" Installing {', '.join(self._missing_deps)}…")
        self._install_worker = InstallWorker(self._selected_env, list(self._missing_deps))
        self._install_worker.finished_install.connect(self._on_missing_deps_installed)
        self._install_worker.start()

    def _on_missing_deps_installed(self, ok: bool):
        self.install_missing_btn.setEnabled(True)
        self.install_missing_btn.setText(" Install missing dependencies into this environment")
        self._render_analysis()

    def _create_env_for_script(self):
        """One-click path from 'this script has missing dependencies' to a working,
        isolated environment — skips the detour through the Environments page."""
        if not self.tool:
            return
        name, ok = QInputDialog.getText(self, "Create environment", "Environment name:", text=self.tool.name)
        if not ok or not name.strip():
            return
        name = name.strip()
        success, error = venv_manager.create_env(name)
        if not success:
            QMessageBox.warning(self, "Could not create environment", error)
            return

        self._populate_run_settings()
        self.env_combo.setCurrentText(name)  # triggers _on_env_selected: persists + re-renders analysis

        deps = [d.name for d in self.tool.dependencies]
        if deps:
            self.create_env_btn.setEnabled(False)
            self.install_missing_btn.setEnabled(False)
            self.install_missing_btn.show()
            self.install_missing_btn.setText(f" Installing {', '.join(deps)}…")
            self._install_worker = InstallWorker(name, deps)
            self._install_worker.finished_install.connect(self._on_env_created_and_installed)
            self._install_worker.start()

    def _on_env_created_and_installed(self, ok: bool):
        self.create_env_btn.setEnabled(True)
        self.install_missing_btn.setEnabled(True)
        self.install_missing_btn.setText(" Install missing dependencies into this environment")
        self._render_analysis()

    # ---- analysis + form rendering ----

    def _render_analysis(self):
        text = (
            f"<b style='color:{COLORS['text']}'>Script:</b> {html.escape(self.tool.script_path)}<br>"
            f"<b style='color:{COLORS['text']}'>Interpreter:</b> {self.tool.interpreter}<br>"
            f"<b style='color:{COLORS['text']}'>Parameters detected:</b> {len(self.tool.parameters)}"
        )
        if self.tool.description:
            text += f"<br><b style='color:{COLORS['text']}'>Description:</b> {html.escape(self.tool.description)}"

        if self._selected_env:
            text += f"<br><b style='color:{COLORS['text']}'>Environment:</b> {html.escape(self._selected_env)}"

        self._interpreter_ok, install_hint = check_interpreter(self.tool, self._selected_env)
        if not self._interpreter_ok:
            bin_name = interpreter_bin(self.tool, self._selected_env)
            text += (
                f"<br><br><span style='color:{COLORS['danger']}'>✗ '{bin_name}' was not found on this system.</span><br>"
                f"<span style='color:{COLORS['text_dim']}'>{install_hint}</span>"
            )

        self._missing_deps = []
        if self.tool.dependencies:
            text += f"<br><br><b style='color:{COLORS['text']}'>Dependencies:</b><br>"
            for dep, status in check_dependencies(self.tool, self._selected_env):
                if status is True:
                    text += f"<span style='color:{COLORS['success']}'>✓ {dep.name}</span><br>"
                elif status is False:
                    self._missing_deps.append(dep.name)
                    install_cmd = dep.pip_install or dep.conda_install
                    text += (
                        f"<span style='color:{COLORS['danger']}'>✗ {dep.name} — not installed</span> "
                        f"<span style='color:{COLORS['text_dim']}'>({install_cmd})</span><br>"
                    )
                else:
                    text += f"<span style='color:{COLORS['text_dim']}'>? {dep.name} — cannot verify</span><br>"
        else:
            text += f"<br><br><b style='color:{COLORS['text']}'>Dependencies:</b> none (standard library only)"

        self.install_missing_btn.setVisible(bool(self._missing_deps) and self._selected_env is not None)
        self.create_env_btn.setVisible(
            self.tool.interpreter == "python" and bool(self.tool.dependencies) and self._selected_env is None
        )

        if not self.tool.parameters:
            text += (
                f"<br><br><span style='color:{COLORS['warning']}'>⚠ No command-line parameters found.</span> "
                "This script likely has hardcoded input/output paths, or reads them interactively "
                "(input() prompts) rather than through argparse/optparse flags — edit the script to "
                "add flags for anything that should be configurable here. Running it as-is will use "
                "whatever paths are hardcoded inside the script."
            )

        if _uses_interactive_input(self.tool):
            text += (
                f"<br><br><span style='color:{COLORS['warning']}'>⚠ This script waits for typed input</span> "
                "(input()/readline()) while running. ScriptOS runs scripts non-interactively, so any such "
                "call will fail immediately instead of hanging — move those values to command-line flags."
            )

        if self.tool.interpreter == "python":
            risks = scan_risks(self.tool.script_path)
            if risks:
                risk_lines = "<br>".join(html.escape(r) for r in risks)
                text += (
                    f"<br><br><span style='color:{COLORS['danger']}'>⚠ This script contains potentially "
                    f"risky code:</span><br>{risk_lines}<br>"
                    f"<span style='color:{COLORS['text_dim']}'>Not a security verdict — just a heads-up. "
                    "Review the script if you don't trust its source before running it.</span>"
                )

        self.analysis_card.setText(text)

    def _render_form(self):
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.inputs.clear()

        for param in self.tool.parameters:
            if param.param_type in _INPUT_FILE_TYPES:
                field = FileField(param.param_type, param.extensions, enable_dnd=True)
            elif param.param_type == ParameterType.FILE_OUT:
                field = FileField(param.param_type, enable_dnd=False)
            elif param.param_type == ParameterType.BOOL:
                field = BoolField()
            else:
                field = QLineEdit()
            if param.default is not None:
                field.setText(str(param.default))
            if param.description:
                field.setToolTip(param.description)
            field.textChanged.connect(self._refresh)
            self.inputs[param.name] = field

            card = QWidget()
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(0, 0, 0, 0)
            card_layout.setSpacing(4)
            label = QLabel(param.label + (" *" if param.required else ""))
            label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; font-weight: 500;")
            card_layout.addWidget(label)
            card_layout.addWidget(field)
            if param.param_type in _INPUT_FILE_TYPES or param.param_type == ParameterType.FILE_OUT:
                card.setFixedWidth(280)
            elif param.param_type == ParameterType.BOOL:
                card.setFixedWidth(130)
            else:
                card.setFixedWidth(190)
            self.form_layout.addWidget(card)
        self._refresh()

    def _values(self) -> dict:
        return {name: field.text() for name, field in self.inputs.items()}

    def _refresh(self):
        if not self.tool:
            return
        values = self._values()
        command = build_command(self.tool, values, self._selected_env)
        self.command_preview.setText(shlex.join(command))

        output_param = _find_output_param(self.tool)
        location = self._resolve_output_location()
        self.output_location_edit_btn.setVisible(output_param is None)
        if output_param:
            self.output_location_label.setText(
                f"Results go to: {location or '(set below)'}  —  set via '{output_param.label}'"
            )
        else:
            self.output_location_label.setText(f"Run logs & results saved to: {location}")

        results = validate_all(self.tool.parameters, values)
        lines = []
        for level, msg in results:
            icon = {"ok": "✓", "warning": "⚠", "error": "✗"}[level]
            lines.append(f"{icon} {msg}")
        self.validation_label.setText("\n".join(lines))
        self.run_btn.setEnabled(is_runnable(results) and self._interpreter_ok)

    # ---- running the tool ----

    def _current_runs_base(self) -> Path:
        # if the script has its own output param, bookkeeping still lives in the default
        # runs/ folder — the script's own field is what the user actually cares about
        return Path(self._default_runs_dir() if _find_output_param(self.tool) else self._resolve_output_location())

    def _parsed_limit(self, field: QLineEdit) -> float | None:
        text = field.text().strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def run_tool(self):
        command = build_command(self.tool, self._values(), self._selected_env)
        runs_base = self._current_runs_base()
        extra_env = credentials.resolve_env(self._selected_credential_set) if self._selected_credential_set else None
        max_memory_mb = self._parsed_limit(self.memory_limit_edit)
        max_cpu_percent = self._parsed_limit(self.cpu_limit_edit)
        self.log_view.clear()
        self.run_btn.hide()
        self.stop_btn.show()

        self.worker = RunWorker(self.tool.name, command, runs_base, extra_env, max_memory_mb, max_cpu_percent)
        self.worker.line_received.connect(self._append_log)
        self.worker.finished_run.connect(self._on_finished)
        self.worker.start()

    def stop_run(self):
        if self.worker:
            self.worker.stop()
        self.stop_btn.setEnabled(False)

    def _append_log(self, stream: str, text: str):
        color = COLORS["danger"] if stream == "stderr" else COLORS["text_dim"]
        self.log_view.appendHtml(f'<span style="color:{color}">{html.escape(text)}</span>')

    def _render_outputs(self, run_dir: Path):
        self.files_list.clear()

        def add_section(title: str, files: list[Path]):
            if not files:
                return
            header = QListWidgetItem(title)
            header.setFlags(Qt.NoItemFlags)
            header.setForeground(Qt.gray)
            self.files_list.addItem(header)
            for f in sorted(files):
                item = QListWidgetItem(f"   {f.name}")
                item.setData(Qt.UserRole, str(f))
                self.files_list.addItem(item)

        add_section("Run log (ScriptOS bookkeeping)", sorted(run_dir.glob("*")))

        values = self._values()
        output_files: list[Path] = []
        for param in self.tool.parameters:
            value = values.get(param.name)
            if not value:
                continue
            path = Path(value)
            if param.param_type == ParameterType.FILE_OUT and path.exists():
                output_files.append(path)
            elif param.param_type == ParameterType.DIRECTORY and path.is_dir():
                output_files.extend(p for p in path.iterdir() if p.is_file())
        add_section("Script output", output_files)

        if self.files_list.count() == 0:
            placeholder = QListWidgetItem("No output files found.")
            placeholder.setFlags(Qt.NoItemFlags)
            self.files_list.addItem(placeholder)

    def _open_file_item(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _render_report(self, exit_code: int, duration: float, run_dir: Path):
        status = "Stopped" if exit_code < 0 else ("Success" if exit_code == 0 else f"Failed (exit {exit_code})")
        lines = [
            f"Run: {run_dir.name}",
            f"Status: {status}",
            f"Duration: {duration:.1f}s",
            "",
            f"Script: {self.tool.script_path}",
            f"Interpreter: {self.tool.interpreter}",
            "",
            f"Command: {shlex.join(build_command(self.tool, self._values()))}",
            "",
            "Parameters:",
        ]
        for name, value in self._values().items():
            if value:
                lines.append(f"  {name}: {value}")
        self.report_view.setPlainText("\n".join(lines))

    def _on_finished(self, exit_code: int, duration: float):
        if exit_code < 0:
            status = "⏹ Stopped"
        elif exit_code == 0:
            status = "✓ Success"
        else:
            status = f"✗ Exit code {exit_code}"
        self.log_view.appendHtml(f"<b>{status} — {duration:.1f}s</b>")

        self.stop_btn.hide()
        self.stop_btn.setEnabled(True)
        self.run_btn.show()
        self._refresh()

        if self.worker and self.worker.run_dir:
            self._render_outputs(self.worker.run_dir)
            self._render_report(exit_code, duration, self.worker.run_dir)
        self._refresh_history()
