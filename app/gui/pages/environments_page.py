"""Environments & Secrets Wallet: create/manage isolated Python venvs and
encrypted credential sets, and see which scripts each is activated for."""
import html
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.environments import assignments, credentials, dir_wallet, venv_manager
from app.gui.icons import lucide_icon
from app.gui.theme import COLORS
from app.gui.workers import InstallWorker

_NO_ENV_LABEL = "System Python"
_NO_DIR_LABEL = "(none)"


class EnvironmentsPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(14)

        header = QHBoxLayout()
        back_btn = QPushButton(" Back")
        back_btn.setObjectName("linkButton")
        back_btn.setIcon(lucide_icon("arrow-left", color=COLORS["text_dim"]))
        back_btn.clicked.connect(self.window.leave_environments)
        title = QLabel("Environments & Secrets Wallet")
        title.setObjectName("heading")
        header.addWidget(back_btn)
        header.addWidget(title)
        header.addStretch()
        outer.addLayout(header)

        tabs = QTabWidget()
        tabs.addTab(self._build_environments_tab(), "Environments")
        tabs.addTab(self._build_wallet_tab(), "Secrets Wallet")
        tabs.addTab(self._build_power_terminal_tab(), "Power Terminal")
        outer.addWidget(tabs, stretch=1)

    def _build_environments_tab(self) -> QWidget:
        tab = QWidget()
        env_col = QVBoxLayout(tab)
        env_col.setSpacing(10)
        env_hint = QLabel(
            "Isolated Python installs, kept entirely inside ~/.scriptos — never touches your system Python. "
            "Activate one for a script via the Environment dropdown above its parameter form; "
            "ScriptOS remembers that choice next time you load the same script."
        )
        env_hint.setWordWrap(True)
        env_col.addWidget(env_hint)

        self.env_list = QListWidget()
        self.env_list.currentItemChanged.connect(self._render_env_detail)
        env_col.addWidget(self.env_list, stretch=1)

        env_btn_row = QHBoxLayout()
        new_env_btn = QPushButton(" New environment")
        new_env_btn.setIcon(lucide_icon("file-input", color=COLORS["text"]))
        new_env_btn.clicked.connect(self._new_environment)
        delete_env_btn = QPushButton("Delete")
        delete_env_btn.clicked.connect(self._delete_environment)
        env_btn_row.addWidget(new_env_btn)
        env_btn_row.addWidget(delete_env_btn)
        env_col.addLayout(env_btn_row)

        self.env_detail_label = QLabel("")
        self.env_detail_label.setWordWrap(True)
        self.env_detail_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        env_col.addWidget(self.env_detail_label)

        self.env_packages_list = QListWidget()
        self.env_packages_list.setMaximumHeight(120)
        env_col.addWidget(self.env_packages_list)

        terminal_label = QLabel("TERMINAL")
        terminal_label.setObjectName("sectionLabel")
        env_col.addWidget(terminal_label)
        terminal_row = QHBoxLayout()
        self.env_terminal_cmd = QLineEdit()
        self.env_terminal_cmd.setReadOnly(True)
        self.env_terminal_cmd.setStyleSheet(f"font-family: 'JetBrains Mono', monospace; color: {COLORS['text_dim']};")
        copy_cmd_btn = QPushButton()
        copy_cmd_btn.setObjectName("ghostIcon")
        copy_cmd_btn.setIcon(lucide_icon("file-input", color=COLORS["text_dim"]))
        copy_cmd_btn.setToolTip("Copy to clipboard")
        copy_cmd_btn.clicked.connect(self._copy_terminal_cmd)
        terminal_row.addWidget(self.env_terminal_cmd, stretch=1)
        terminal_row.addWidget(copy_cmd_btn)
        env_col.addLayout(terminal_row)
        terminal_hint = QLabel("Runs the equivalent of 'scriptos activate <name>' — same environment, plain shell.")
        terminal_hint.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        terminal_hint.setWordWrap(True)
        env_col.addWidget(terminal_hint)

        install_row = QHBoxLayout()
        self.env_install_edit = QLineEdit()
        self.env_install_edit.setPlaceholderText("package name, e.g. pandas")
        install_btn = QPushButton("Install")
        install_btn.clicked.connect(self._install_package_in_selected_env)
        install_row.addWidget(self.env_install_edit, stretch=1)
        install_row.addWidget(install_btn)
        env_col.addLayout(install_row)

        self.env_install_log = QPlainTextEdit()
        self.env_install_log.setReadOnly(True)
        self.env_install_log.setMaximumHeight(90)
        self.env_install_log.hide()
        env_col.addWidget(self.env_install_log)
        return tab

    def _build_wallet_tab(self) -> QWidget:
        tab = QWidget()
        cred_col = QVBoxLayout(tab)
        cred_col.setSpacing(10)
        cred_hint = QLabel(
            "For scripts that need a password, API key, or login token. Store it here once, in a "
            "named set (e.g. 'Lab Database') — ScriptOS hands it to the script securely at run time. "
            "You never paste secrets into the script itself or see them typed out in the command preview.\n\n"
            "Stored only on this computer, inside ScriptOS's own folder (~/.scriptos), encrypted — "
            "not in your Mac's Keychain, not in any cloud."
        )
        cred_hint.setWordWrap(True)
        cred_col.addWidget(cred_hint)

        self.cred_list = QListWidget()
        self.cred_list.currentItemChanged.connect(self._render_cred_detail)
        cred_col.addWidget(self.cred_list, stretch=1)

        cred_btn_row = QHBoxLayout()
        new_cred_btn = QPushButton(" New set")
        new_cred_btn.setIcon(lucide_icon("file-input", color=COLORS["text"]))
        new_cred_btn.clicked.connect(self._new_credential_set)
        delete_cred_btn = QPushButton("Delete set")
        delete_cred_btn.clicked.connect(self._delete_credential_set)
        cred_btn_row.addWidget(new_cred_btn)
        cred_btn_row.addWidget(delete_cred_btn)
        cred_col.addLayout(cred_btn_row)

        self.cred_detail_label = QLabel("")
        self.cred_detail_label.setWordWrap(True)
        self.cred_detail_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px;")
        cred_col.addWidget(self.cred_detail_label)

        self.cred_keys_list = QListWidget()
        self.cred_keys_list.setMaximumHeight(120)
        cred_col.addWidget(self.cred_keys_list)

        cred_key_row = QHBoxLayout()
        add_secret_btn = QPushButton(" Add secret")
        add_secret_btn.setIcon(lucide_icon("file-input", color=COLORS["text"]))
        add_secret_btn.clicked.connect(self._add_secret_to_selected_set)
        remove_secret_btn = QPushButton("Remove selected")
        remove_secret_btn.clicked.connect(self._remove_selected_secret)
        cred_key_row.addWidget(add_secret_btn)
        cred_key_row.addWidget(remove_secret_btn)
        cred_col.addLayout(cred_key_row)

        return tab

    def _build_power_terminal_tab(self) -> QWidget:
        tab = QWidget()
        col = QVBoxLayout(tab)
        col.setSpacing(10)
        hint = QLabel(
            "Pick an environment and a saved directory, then work from a plain terminal — "
            "no need to keep a tab open just to stay in the right place."
        )
        hint.setWordWrap(True)
        col.addWidget(hint)

        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("Environment:"))
        self.pt_env_combo = QComboBox()
        self.pt_env_combo.currentTextChanged.connect(self._update_power_terminal_cmd)
        picker_row.addWidget(self.pt_env_combo, stretch=1)
        picker_row.addWidget(QLabel("Directory:"))
        self.pt_dir_combo = QComboBox()
        self.pt_dir_combo.currentTextChanged.connect(self._update_power_terminal_cmd)
        picker_row.addWidget(self.pt_dir_combo, stretch=1)
        col.addLayout(picker_row)

        dir_btn_row = QHBoxLayout()
        add_dir_btn = QPushButton(" Save a directory")
        add_dir_btn.setIcon(lucide_icon("folder-open", color=COLORS["text"]))
        add_dir_btn.clicked.connect(self._new_saved_dir)
        delete_dir_btn = QPushButton("Remove selected directory")
        delete_dir_btn.clicked.connect(self._delete_saved_dir)
        dir_btn_row.addWidget(add_dir_btn)
        dir_btn_row.addWidget(delete_dir_btn)
        col.addLayout(dir_btn_row)

        cmd_row = QHBoxLayout()
        self.pt_cmd_line = QLineEdit()
        self.pt_cmd_line.setReadOnly(True)
        self.pt_cmd_line.setStyleSheet(f"font-family: 'JetBrains Mono', monospace; color: {COLORS['text_dim']};")
        copy_btn = QPushButton()
        copy_btn.setObjectName("ghostIcon")
        copy_btn.setIcon(lucide_icon("file-input", color=COLORS["text_dim"]))
        copy_btn.setToolTip("Copy to clipboard")
        copy_btn.clicked.connect(self._copy_power_terminal_cmd)
        cmd_row.addWidget(self.pt_cmd_line, stretch=1)
        cmd_row.addWidget(copy_btn)
        col.addLayout(cmd_row)

        open_btn = QPushButton("Open Terminal here")
        open_btn.setObjectName("primary")
        open_btn.clicked.connect(self._open_power_terminal)
        col.addWidget(open_btn)
        col.addStretch()
        return tab

    def _refresh_power_terminal(self):
        self.pt_env_combo.blockSignals(True)
        self.pt_env_combo.clear()
        self.pt_env_combo.addItem(_NO_ENV_LABEL)
        self.pt_env_combo.addItems(venv_manager.list_envs())
        self.pt_env_combo.blockSignals(False)

        self.pt_dir_combo.blockSignals(True)
        self.pt_dir_combo.clear()
        self.pt_dir_combo.addItem(_NO_DIR_LABEL)
        self.pt_dir_combo.addItems(dir_wallet.list_dirs())
        self.pt_dir_combo.blockSignals(False)
        self._update_power_terminal_cmd()

    def _update_power_terminal_cmd(self):
        parts = []
        dir_name = self.pt_dir_combo.currentText()
        if dir_name and dir_name != _NO_DIR_LABEL:
            path = dir_wallet.get_path(dir_name)
            if path:
                parts.append(f"cd {path}")
        env_name = self.pt_env_combo.currentText()
        if env_name and env_name != _NO_ENV_LABEL:
            parts.append(f"source {venv_manager.env_dir(env_name)}/bin/activate")
        self.pt_cmd_line.setText(" && ".join(parts))

    def _new_saved_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Save a directory")
        if not path:
            return
        name, ok = QInputDialog.getText(self, "Save directory", "Name for this directory:", text=Path(path).name)
        if not ok or not name.strip():
            return
        dir_wallet.add_dir(name.strip(), path)
        self._refresh_power_terminal()

    def _delete_saved_dir(self):
        name = self.pt_dir_combo.currentText()
        if name and name != _NO_DIR_LABEL:
            dir_wallet.delete_dir(name)
            self._refresh_power_terminal()

    def _copy_power_terminal_cmd(self):
        if self.pt_cmd_line.text():
            QApplication.clipboard().setText(self.pt_cmd_line.text())

    def _open_power_terminal(self):
        command = self.pt_cmd_line.text()
        if not command:
            QMessageBox.information(self, "Nothing to open", "Pick an environment and/or a directory first.")
            return
        script = command.replace("\\", "\\\\").replace('"', '\\"')
        try:
            subprocess.run(["osascript", "-e", f'tell application "Terminal" to do script "{script}"'], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            QMessageBox.warning(self, "Could not open Terminal", str(exc))

    def refresh(self):
        self.env_list.clear()
        for name in venv_manager.list_envs():
            self.env_list.addItem(name)
        self.env_packages_list.clear()
        self.env_install_log.hide()
        self._refresh_power_terminal()

        self.cred_list.clear()
        for name in credentials.list_sets():
            self.cred_list.addItem(name)
        self.cred_keys_list.clear()

    def _render_env_detail(self, current: QListWidgetItem | None, _previous=None):
        self.env_packages_list.clear()
        if not current:
            self.env_detail_label.setText("")
            self.env_terminal_cmd.setText("")
            return
        name = current.text()
        self.env_terminal_cmd.setText(f"source {venv_manager.env_dir(name)}/bin/activate")
        used_by = assignments.scripts_using_env(name)
        used_text = (
            "<br>".join(html.escape(Path(p).name) for p in used_by)
            if used_by else "not activated for any script yet"
        )
        self.env_detail_label.setText(
            f"<b style='color:{COLORS['text']}'>Location:</b> {html.escape(str(venv_manager.env_dir(name)))}<br>"
            f"<b style='color:{COLORS['text']}'>Activated for:</b><br>{used_text}"
        )
        for pkg in venv_manager.list_installed(name):
            self.env_packages_list.addItem(pkg)

    def _new_environment(self):
        name, ok = QInputDialog.getText(self, "New environment", "Name (e.g. 'bioinformatics'):")
        if not ok or not name.strip():
            return
        success, error = venv_manager.create_env(name.strip())
        if not success:
            self.env_install_log.show()
            self.env_install_log.setPlainText(f"Could not create environment: {error}")
            return
        self.refresh()

    def _delete_environment(self):
        item = self.env_list.currentItem()
        if not item:
            return
        name = item.text()
        venv_manager.delete_env(name)
        for script_path in assignments.scripts_using_env(name):
            assignments.set_assigned_env(script_path, None)
        self.refresh()

    def _copy_terminal_cmd(self):
        if self.env_terminal_cmd.text():
            QApplication.clipboard().setText(self.env_terminal_cmd.text())

    def _install_package_in_selected_env(self):
        item = self.env_list.currentItem()
        package = self.env_install_edit.text().strip()
        if not item or not package:
            return
        self.env_install_log.show()
        self.env_install_log.setPlainText(f"Installing {package} into '{item.text()}'…")
        self._install_worker = InstallWorker(item.text(), [package])
        self._install_worker.line_received.connect(lambda line: self.env_install_log.appendPlainText(line))
        self._install_worker.finished_install.connect(lambda ok: self._on_install_finished(item.text(), ok))
        self._install_worker.start()

    def _on_install_finished(self, env_name: str, ok: bool):
        self.env_install_log.appendPlainText("Done." if ok else "Install failed — see log above.")
        self.env_install_edit.clear()
        for i in range(self.env_list.count()):
            if self.env_list.item(i).text() == env_name:
                self._render_env_detail(self.env_list.item(i))
                break

    def _render_cred_detail(self, current: QListWidgetItem | None, _previous=None):
        self.cred_keys_list.clear()
        if not current:
            self.cred_detail_label.setText("")
            return
        name = current.text()
        used_by = assignments.scripts_using_credentials(name)
        used_text = (
            "<br>".join(html.escape(Path(p).name) for p in used_by)
            if used_by else "not activated for any script yet"
        )
        self.cred_detail_label.setText(f"<b style='color:{COLORS['text']}'>Activated for:</b><br>{used_text}")
        for key in credentials.get_keys(name):
            self.cred_keys_list.addItem(key)

    def _new_credential_set(self):
        name, ok = QInputDialog.getText(self, "New credential set", "Name (e.g. 'Lab Database'):")
        if not ok or not name.strip():
            return
        # a set only really exists once it has a key — prompt for the first one right away
        self._prompt_add_secret(name.strip())
        self.refresh()

    def _delete_credential_set(self):
        item = self.cred_list.currentItem()
        if not item:
            return
        name = item.text()
        credentials.delete_set(name)
        for script_path in assignments.scripts_using_credentials(name):
            assignments.set_assigned_credentials(script_path, None)
        self.refresh()

    def _add_secret_to_selected_set(self):
        item = self.cred_list.currentItem()
        if not item:
            return
        self._prompt_add_secret(item.text())
        self._render_cred_detail(item)

    def _prompt_add_secret(self, set_name: str):
        key, ok = QInputDialog.getText(self, "Add secret", "Key name (e.g. API_KEY):")
        if not ok or not key.strip():
            return
        value, ok = QInputDialog.getText(self, "Add secret", f"Value for {key}:", QLineEdit.Password)
        if not ok or not value:
            return
        credentials.set_secret(set_name, key.strip(), value)

    def _remove_selected_secret(self):
        set_item = self.cred_list.currentItem()
        key_item = self.cred_keys_list.currentItem()
        if not set_item or not key_item:
            return
        credentials.delete_key(set_item.text(), key_item.text())
        self._render_cred_detail(set_item)
