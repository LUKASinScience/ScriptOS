"""Main window: nav bar, native menu bar, and the page stack. Each page owns
its own UI and state (app/gui/pages/); this file only coordinates navigation
between them.

Workflow: empty drop zone (load a script) -> script analysis + auto-generated
form only becomes visible once a script is loaded -> run -> live log.
"""
import os
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QMainWindow, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from app.gui.icons import lucide_icon
from app.gui.pages.empty_state import EmptyStatePage
from app.gui.pages.environments_page import EnvironmentsPage
from app.gui.pages.workflows_page import WorkflowsPage
from app.gui.pages.workspace_page import WorkspacePage
from app.gui.theme import COLORS, STYLESHEET, THEME_NAME, save_theme_name
from app.storage.recent_tools import load_recent

_EMPTY, _WORKSPACE, _ENVIRONMENTS, _WORKFLOWS = range(4)


class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ScriptOS")
        self.resize(1000, 750)
        self.setStyleSheet(STYLESHEET)
        self.setAcceptDrops(True)

        self._page_before_side = _EMPTY

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        nav_bar = QHBoxLayout()
        nav_bar.setContentsMargins(16, 8, 16, 8)
        home_btn = QPushButton(" ScriptOS")
        home_btn.setObjectName("linkButton")
        home_btn.setIcon(lucide_icon("house", color=COLORS["text_dim"]))
        home_btn.setToolTip("Back to your scripts")
        home_btn.clicked.connect(self.go_home)
        workflows_nav_btn = QPushButton(" Workflows")
        workflows_nav_btn.setObjectName("linkButton")
        workflows_nav_btn.setIcon(lucide_icon("play", color=COLORS["text_dim"]))
        workflows_nav_btn.clicked.connect(self.go_to_workflows)
        env_nav_btn = QPushButton(" Environments")
        env_nav_btn.setObjectName("linkButton")
        env_nav_btn.setIcon(lucide_icon("folder-open", color=COLORS["text_dim"]))
        env_nav_btn.clicked.connect(self.go_to_environments)
        nav_bar.addWidget(home_btn)
        nav_bar.addStretch()
        nav_bar.addWidget(workflows_nav_btn)
        nav_bar.addWidget(env_nav_btn)
        root_layout.addLayout(nav_bar)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.empty_state_page = EmptyStatePage(self)
        self.workspace_page = WorkspacePage(self)
        self.environments_page = EnvironmentsPage(self)
        self.workflows_page = WorkflowsPage(self)
        self.stack.addWidget(self.empty_state_page)
        self.stack.addWidget(self.workspace_page)
        self.stack.addWidget(self.environments_page)
        self.stack.addWidget(self.workflows_page)

        self.empty_state_page.refresh()
        self._build_menu_bar()

    # ---- native menu bar (the app menu next to the Apple logo on macOS) ----

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        load_action = QAction("Load Script…", self)
        load_action.setShortcut(QKeySequence.Open)
        load_action.triggered.connect(self.load_script)
        file_menu.addAction(load_action)
        self.recent_menu = file_menu.addMenu("Recent Scripts")
        self.refresh_recent_menu()

        env_menu = menu_bar.addMenu("&Environments")
        manage_action = QAction("Manage Environments && Wallet…", self)
        manage_action.setShortcut(QKeySequence("Ctrl+E"))
        manage_action.triggered.connect(self.go_to_environments)
        env_menu.addAction(manage_action)
        env_menu.addSeparator()
        new_env_action = QAction("New Environment…", self)
        new_env_action.triggered.connect(self._menu_new_environment)
        env_menu.addAction(new_env_action)
        new_secret_action = QAction("New Secret Set…", self)
        new_secret_action.triggered.connect(self._menu_new_credential_set)
        env_menu.addAction(new_secret_action)

        view_menu = menu_bar.addMenu("&View")
        appearance_menu = view_menu.addMenu("Appearance")
        appearance_group = QActionGroup(self)
        appearance_group.setExclusive(True)
        dark_action = QAction("Dark", self, checkable=True)
        dark_action.setChecked(THEME_NAME != "light")
        dark_action.triggered.connect(lambda: self._set_theme("dark"))
        light_action = QAction("Light", self, checkable=True)
        light_action.setChecked(THEME_NAME == "light")
        light_action.triggered.connect(lambda: self._set_theme("light"))
        for action in (dark_action, light_action):
            appearance_group.addAction(action)
            appearance_menu.addAction(action)

        help_menu = menu_bar.addMenu("&Help")
        guide_action = QAction("ScriptOS Guide", self)
        guide_action.triggered.connect(self._open_guide)
        help_menu.addAction(guide_action)
        about_action = QAction("About ScriptOS", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def refresh_recent_menu(self):
        self.recent_menu.clear()
        entries = [e for e in load_recent() if Path(e["path"]).exists()]
        if not entries:
            empty_action = QAction("No recent scripts", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
            return
        for entry in entries:
            action = QAction(entry["name"], self)
            action.triggered.connect(lambda checked=False, p=entry["path"]: self.open_script(p))
            self.recent_menu.addAction(action)

    def _menu_new_environment(self):
        self.go_to_environments()
        self.environments_page._new_environment()

    def _menu_new_credential_set(self):
        self.go_to_environments()
        self.environments_page._new_credential_set()

    def _open_guide(self):
        docs_index = Path(__file__).resolve().parents[2] / "site" / "index.html"
        if docs_index.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(docs_index)))
        else:
            QMessageBox.information(
                self, "ScriptOS Guide",
                "The docs site hasn't been built yet.\nRun: zensical build",
            )

    def _set_theme(self, name: str):
        if name == THEME_NAME:
            return
        save_theme_name(name)
        choice = QMessageBox.question(
            self, "Restart required",
            f"Switching to {name} mode takes effect after ScriptOS restarts. Restart now?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
        )
        if choice == QMessageBox.Yes:
            os.execv(sys.executable, [sys.executable, *sys.argv])

    def _show_about(self):
        QMessageBox.about(
            self, "About ScriptOS",
            "ScriptOS\n\nTurns a Python or R script into a validated, reproducible desktop app.\n"
            "No terminal required.",
        )

    # ---- drag & drop of a script onto the whole window ----

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].toLocalFile().lower().endswith((".py", ".r")):
            self.open_script(urls[0].toLocalFile())

    # ---- navigation ----

    def load_script(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load script", "", "Scripts (*.py *.R)")
        if path:
            self.open_script(path)

    def open_script(self, path: str):
        self.workspace_page.load_path(path)
        self.stack.setCurrentIndex(_WORKSPACE)

    def go_to_empty_state(self):
        self.empty_state_page.refresh()
        self.stack.setCurrentIndex(_EMPTY)

    def go_home(self):
        """The always-visible way back to where you work with scripts — the loaded
        tool's workspace if one is open, otherwise the load-a-script screen."""
        if self.workspace_page.tool:
            self.stack.setCurrentIndex(_WORKSPACE)
        else:
            self.go_to_empty_state()

    def _remember_page_before_side(self):
        current = self.stack.currentIndex()
        self._page_before_side = _EMPTY if current in (_ENVIRONMENTS, _WORKFLOWS) else current

    def go_to_environments(self):
        self._remember_page_before_side()
        self.environments_page.refresh()
        self.stack.setCurrentIndex(_ENVIRONMENTS)

    def leave_environments(self):
        self.workspace_page.on_return_from_side_page()
        self.stack.setCurrentIndex(self._page_before_side)

    def go_to_workflows(self):
        self._remember_page_before_side()
        self.workflows_page.refresh()
        self.stack.setCurrentIndex(_WORKFLOWS)

    def leave_workflows(self):
        self.stack.setCurrentIndex(self._page_before_side)
