import sys
import os
import logging
import subprocess
import tempfile
import platform
import winreg
from typing import Callable, List, Tuple

from PyQt5.QtCore import Qt, QObject, QRunnable, QThreadPool, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QStackedWidget, QLabel, QPushButton, QPlainTextEdit,
    QScrollArea, QMessageBox, QSplitter, QSizePolicy, QCheckBox, QProgressBar,
    QGroupBox, QGridLayout, QTextEdit, QComboBox, QGraphicsOpacityEffect, QTextBrowser
)

# Ensure repo root on sys.path so 'components' is importable
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import components
from components import debloat_windows
from components.utils import check_admin_privileges, get_system_info


# ---------- Logging bridge to GUI ----------
class QtLogBridge(QObject):
    message = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    def __init__(self, bridge: QtLogBridge):
        super().__init__()
        self.bridge = bridge

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        self.bridge.message.emit(msg)


# ---------- Single worker ----------
class WorkerSignals(QObject):
    finished = pyqtSignal(bool, str)   # ok, name
    error = pyqtSignal(str, str)       # name, error
    started = pyqtSignal(str)          # name
    progress = pyqtSignal(str)         # message


class Worker(QRunnable):
    def __init__(self, name: str, func: Callable[[], bool]):
        super().__init__()
        self.name = name
        self.func = func
        self.signals = WorkerSignals()

    def run(self):
        self.signals.started.emit(self.name)
        try:
            ok = bool(self.func())
            self.signals.finished.emit(ok, self.name)
        except Exception as e:
            self.signals.error.emit(self.name, str(e))


# ---------- Batch worker (sequential) ----------
class BatchWorker(QRunnable):
    def __init__(self, tasks: List[Tuple[str, Callable[[], bool]]], prehook: Callable[[], None] | None = None):
        super().__init__()
        self.tasks = tasks
        self.prehook = prehook
        self.signals = WorkerSignals()

    def run(self):
        # Pre-hook (e.g., one-time connectivity check)
        if self.prehook:
            try:
                self.signals.progress.emit(">>> Running initial connectivity check...")
                self.prehook()
                self.signals.progress.emit("Connectivity check completed.")
            except Exception as e:
                self.signals.progress.emit(f"Connectivity check error: {e}")

        total = len(self.tasks)
        success = 0
        for i, (name, func) in enumerate(self.tasks, 1):
            self.signals.progress.emit(f">>> [{i}/{total}] Running: {name}")
            try:
                ok = bool(func())
                if ok:
                    success += 1
                    self.signals.progress.emit(f"{name} completed.")
                else:
                    self.signals.progress.emit(f"{name} finished with warnings.")
            except Exception as e:
                self.signals.error.emit(name, str(e))
        self.signals.finished.emit(success == total, f"{success}/{total} tasks succeeded")


# ---------- Main window ----------
class ZTalonGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZTalon - Windows Optimizer & Debloater")
        self.setMinimumSize(1200, 800)

        # Storage for checkboxes and flags (init early)
        self._checkboxes = {}
        self._connectivity_checked = False
        self._info_shown = False

        icon_path = os.path.join(ROOT_DIR, "ICON.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.thread_pool = QThreadPool.globalInstance()

        # Ultra-modern dark theme with animations and effects
        self.setStyleSheet("""
            QMainWindow { 
                background-color: #1e1e2e; 
            }
            QListWidget { 
                background-color: #181825; 
                color: #cdd6f4; 
                border: 1px solid #313244;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item { 
                padding: 12px; 
                border-radius: 6px;
                margin: 2px;
            }
            QListWidget::item:selected { 
                background-color: #89b4fa; 
                color: #1e1e2e;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background-color: #313244;
            }
            QLabel { 
                color: #cdd6f4; 
                font-size: 14px;
            }    
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #313244, stop:1 #262637); 
                color: #cdd6f4; 
                border: 2px solid #45475a; 
                border-radius: 8px; 
                padding: 12px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { 
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #45475a, stop:1 #313244);
                border: 2px solid #89b4fa;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #89b4fa, stop:1 #74c7ec);
                color: #1e1e2e;
                border: 2px solid #74c7ec;
            }
            QPushButton:disabled {
                background-color: #181825;
                color: #585b70;
                border: 1px solid #313244;
            }
            QPlainTextEdit, QTextEdit { 
                background-color: #181825; 
                color: #cdd6f4; 
                border: 1px solid #313244; 
                font-family: 'Consolas', 'Courier New', monospace; 
                font-size: 11px;
                padding: 5px;
            }
            QCheckBox { 
                color: #cdd6f4;
                spacing: 8px;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #45475a;
                border-radius: 4px;
                background-color: #181825;
            }
            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
            }
            QCheckBox::indicator:hover {
                border-color: #89b4fa;
            }
            QProgressBar {
                border: 2px solid #313244;
                border-radius: 8px;
                background-color: #181825;
                text-align: center;
                color: #cdd6f4;
                font-size: 12px;
                font-weight: bold;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #89b4fa, stop:1 #74c7ec);
                border-radius: 6px;
            }
            QGroupBox {
                color: #cdd6f4;
                border: 2px solid #313244;
                border-radius: 8px;
                margin-top: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QScrollArea {
                border: none;
                background-color: #1e1e2e;
            }
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QComboBox:hover {
                border-color: #89b4fa;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #313244;
                color: #cdd6f4;
                selection-background-color: #89b4fa;
                selection-color: #1e1e2e;
            }
        """)

        # Logging -> GUI
        self.log_bridge = QtLogBridge()
        self.log_bridge.message.connect(self.append_log)
        self.install_logging_bridge()

        # Layout
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)

        # Sidebar
        self.menu = QListWidget()
        self.menu.setFixedWidth(250)
        menu_items = [
            "Home",
            "App Installer", 
            "Optimizations",
            "Cleanup",
            "Final Steps",
            "Other Tools",
            "System Info"
        ]
        for item in menu_items:
            self.menu.addItem(QListWidgetItem(item))

        # Pages
        self.pages = QStackedWidget()
        
        # Animation setup for smooth transitions (BEFORE adding pages)
        self.page_opacity = QGraphicsOpacityEffect()
        self.pages.setGraphicsEffect(self.page_opacity)
        self.page_animation = QPropertyAnimation(self.page_opacity, b"opacity")
        self.page_animation.setDuration(200)  # 200ms fast transition
        self.page_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.pages.addWidget(self.build_home_page())             # index 0
        self.pages.addWidget(self.build_app_installer_page())    # index 1
        self.pages.addWidget(self.build_optimizations_page())    # index 2
        self.pages.addWidget(self.build_cleanup_page())          # index 3
        self.pages.addWidget(self.build_final_steps_page())      # index 4
        self.pages.addWidget(self.build_others_page())           # index 5
        self.pages.addWidget(self.build_info_page())             # index 6

        self.menu.currentRowChanged.connect(self.on_menu_changed)
        self.menu.setCurrentRow(0)

        splitter.addWidget(self.menu)
        splitter.addWidget(self.pages)
        splitter.setStretchFactor(1, 1)

        # Logs panel with progress bar
        logs_container = QWidget()
        logs_layout = QVBoxLayout(logs_container)
        logs_layout.setContentsMargins(0, 5, 0, 0)
        
        logs_header = QHBoxLayout()
        logs_label = QLabel("Activity Logs")
        logs_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #89b4fa;")
        self.clear_logs_btn = QPushButton("Clear Logs")
        self.clear_logs_btn.setMaximumWidth(120)
        self.clear_logs_btn.clicked.connect(self.clear_logs)
        logs_header.addWidget(logs_label)
        logs_header.addStretch()
        logs_header.addWidget(self.clear_logs_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(25)
        
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(200)
        
        logs_layout.addLayout(logs_header)
        logs_layout.addWidget(self.progress_bar)
        logs_layout.addWidget(self.log_box)

        central = QWidget()
        main_v = QVBoxLayout(central)
        main_v.setContentsMargins(10, 10, 10, 10)
        main_v.addWidget(splitter)
        main_v.addWidget(logs_container)
        self.setCentralWidget(central)

        # Status
        self.statusBar().showMessage("Ready - ZTalon GUI initialized")
        self.statusBar().setStyleSheet("background-color: #313244; color: #cdd6f4; padding: 5px;")

        # Admin advice
        if not check_admin_privileges():
            QMessageBox.warning(
                self, "Administrator Privileges Required",
                "Some optimizations require Administrator privileges.\n\n"
                "Please run ZTalon as Administrator for full functionality.\n\n"
                "Right-click the executable and select 'Run as Administrator'."
            )
    
    def build_home_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Welcome section
        welcome = QLabel("Welcome to ZTalon")
        welcome.setStyleSheet("""
            font-size: 32px; 
            font-weight: bold; 
            color: #89b4fa; 
            margin-bottom: 5px;
            letter-spacing: 1px;
        """)
        
        subtitle = QLabel("Windows Optimization & Debloating Tool")
        subtitle.setStyleSheet("""
            font-size: 16px; 
            color: #a6adc8; 
            margin-bottom: 20px;
            font-weight: 500;
        """)
        
        description = QLabel(
            "ZTalon helps you optimize and clean your Windows system with powerful tools:\n\n"
            "• Install essential applications automatically\n"
            "• Apply AMD-focused driver debloat and tuning\n"
            "• Remove bloatware and unnecessary Windows components\n"
            "• Improve system performance and responsiveness\n"
            "• Clean temporary files and cache\n"
            "• Configure optimal power and network settings"
        )
        description.setStyleSheet("font-size: 13px; color: #cdd6f4; line-height: 1.6;")
        description.setWordWrap(True)
        
        # Quick actions group
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QGridLayout()
        actions_layout.setSpacing(15)
        
        # Action buttons with better styling
        btn_install_apps = QPushButton("⚡ Install Applications")
        btn_install_apps.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #89b4fa, stop:1 #74c7ec);
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #74c7ec, stop:1 #89dceb);
            }
        """)
        btn_install_apps.setMinimumHeight(55)
        btn_install_apps.clicked.connect(lambda: self.menu.setCurrentRow(1))
        
        btn_optimize = QPushButton("🚀 System Optimizations")
        btn_optimize.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #a6e3a1, stop:1 #94e2d5);
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #94e2d5, stop:1 #89dceb);
            }
        """)
        btn_optimize.setMinimumHeight(55)
        btn_optimize.clicked.connect(lambda: self.menu.setCurrentRow(2))
        
        btn_cleanup = QPushButton("🧹 System Cleanup")
        btn_cleanup.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f9e2af, stop:1 #fab387);
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fab387, stop:1 #eba0ac);
            }
        """)
        btn_cleanup.setMinimumHeight(55)
        btn_cleanup.clicked.connect(lambda: self.menu.setCurrentRow(3))
        
        btn_info = QPushButton("📊 System Information")
        btn_info.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #cba6f7, stop:1 #b4befe);
                color: #1e1e2e;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #b4befe, stop:1 #89b4fa);
            }
        """)
        btn_info.setMinimumHeight(55)
        btn_info.clicked.connect(lambda: self.menu.setCurrentRow(6))
        
        actions_layout.addWidget(btn_install_apps, 0, 0)
        actions_layout.addWidget(btn_optimize, 0, 1)
        actions_layout.addWidget(btn_cleanup, 1, 0)
        actions_layout.addWidget(btn_info, 1, 1)
        
        actions_group.setLayout(actions_layout)
        
        # System checks button
        btn_checks = QPushButton("Run System Checks")
        btn_checks.setStyleSheet("background-color: #45475a; font-size: 14px;")
        btn_checks.setMinimumHeight(40)
        btn_checks.clicked.connect(self.run_system_checks)
        
        # Restart button
        btn_restart = QPushButton("Restart Computer")
        btn_restart.setStyleSheet("background-color: #f38ba8; color: #1e1e2e; font-size: 14px;")
        btn_restart.setMinimumHeight(40)
        btn_restart.clicked.connect(self.restart_computer)
        
        layout.addWidget(welcome)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(description)
        layout.addSpacing(20)
        layout.addWidget(actions_group)
        layout.addSpacing(15)
        layout.addWidget(btn_checks)
        layout.addWidget(btn_restart)
        layout.addStretch()
        
        return page
    
    def build_app_installer_page(self) -> QWidget:
        """Application installer page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Application Installer")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa;")
        
        description = QLabel(
            "Install popular applications automatically using PowerShell script.\n\n"
            "Available applications include:\n"
            "• Utilities: 7-Zip, Notepad++, WinRAR\n"
            "• Browsers: Chrome, Firefox, Brave\n"
            "• Communication: Discord, Telegram\n"
            "• Gaming: Steam, Epic Games, Battle.net\n"
            "• Multimedia: Spotify, VLC Media Player\n"
            "• Development: Git, VS Code, Python\n"
            "• Office: Microsoft Office 2024"
        )
        description.setStyleSheet("font-size: 13px; color: #cdd6f4;")
        description.setWordWrap(True)
        
        warning = QLabel("WARNING: This will open a PowerShell window for application selection")
        warning.setStyleSheet("font-size: 12px; color: #f9e2af; padding: 10px; background-color: #313244; border-radius: 6px;")
        
        btn_run = QPushButton("Run Application Installer")
        btn_run.setMinimumHeight(50)
        btn_run.setStyleSheet("font-size: 15px; background-color: #89b4fa; color: #1e1e2e; font-weight: bold;")
        btn_run.clicked.connect(self.open_app_installer_ps)
        
        layout.addWidget(title)
        layout.addSpacing(10)
        layout.addWidget(description)
        layout.addSpacing(15)
        layout.addWidget(warning)
        layout.addSpacing(15)
        layout.addWidget(btn_run)
        layout.addStretch()
        
        return page

    def build_checklist_section(self, group_key: str, title: str, items: List[Tuple[str, Callable[[], bool], str]]) -> QWidget:
        container = QWidget()
        v = QVBoxLayout(container)
        v.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa; margin-bottom: 10px;")
        v.addWidget(title_label)

        # Scrollable checklist
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setStyleSheet("""
            QScrollArea { 
                background: #1e1e2e; 
                border: 1px solid #313244;
                border-radius: 8px;
            }
            QScrollArea > QWidget {
                background: #1e1e2e;
            }
        """)

        inner = QWidget()
        inner.setStyleSheet("background: #1e1e2e;")
        inner_v = QVBoxLayout(inner)
        inner_v.setSpacing(8)
        inner_v.setContentsMargins(15, 15, 15, 15)

        self._checkboxes[group_key] = []
        for item in items:
            if len(item) == 3:
                label, func, tooltip = item
            else:
                label, func = item
                tooltip = ""
                
            cb = QCheckBox(label)
            cb.setProperty("task_func", func)
            cb.setToolTip(tooltip)
            cb.setStyleSheet("font-size: 13px; padding: 5px;")
            inner_v.addWidget(cb)
            self._checkboxes[group_key].append(cb)

        inner_v.addStretch()
        sc.setWidget(inner)
        v.addWidget(sc)

        # Control buttons
        controls = QHBoxLayout()
        controls.setSpacing(10)
        
        btn_all = QPushButton("Select All")
        btn_clear = QPushButton("Clear All")
        btn_run = QPushButton("Run Selected")
        
        btn_all.setMinimumHeight(35)
        btn_clear.setMinimumHeight(35)
        btn_run.setMinimumHeight(35)
        
        btn_run.setStyleSheet("background-color: #89b4fa; color: #1e1e2e; font-weight: bold;")

        btn_all.clicked.connect(lambda: self.set_checks(group_key, True))
        btn_clear.clicked.connect(lambda: self.set_checks(group_key, False))
        btn_run.clicked.connect(lambda: self.run_selected(group_key))

        controls.addWidget(btn_all)
        controls.addWidget(btn_clear)
        controls.addWidget(btn_run)
        controls.addStretch()
        v.addLayout(controls)

        return container

    def build_optimizations_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(15, 15, 15, 15)
        
        # Registry Tweak Options Group
        options_group = QGroupBox("Registry Configuration")
        options_layout = QGridLayout()
        
        # Taskbar Position
        lbl_pos = QLabel("Taskbar Position:")
        self.combo_taskbar_pos = QComboBox()
        self.combo_taskbar_pos.addItems(["Left (Classic)", "Center (Default)"])
        self.combo_taskbar_pos.setCurrentIndex(0) # Default to Left
        self.combo_taskbar_pos.setToolTip("Choose where the Start button and icons appear on the taskbar.")
        
        # Taskbar Color
        self.chk_black_taskbar = QCheckBox("Apply Black Taskbar")
        self.chk_black_taskbar.setToolTip("Sets the taskbar color to pure black (OLED friendly). May require Explorer restart.")
        
        options_layout.addWidget(lbl_pos, 0, 0)
        options_layout.addWidget(self.combo_taskbar_pos, 0, 1)
        options_layout.addWidget(self.chk_black_taskbar, 1, 0, 1, 2)
        
        options_group.setLayout(options_layout)
        v.addWidget(options_group)

        data = self.get_all_optimizations()
        section = self.build_checklist_section("optimizations", "System Optimizations", data)
        v.addWidget(section)
        return page

    def run_registry_changes_gui(self) -> bool:
        """Wrapper to run registry changes with GUI parameters"""
        # 0 = Left, 1 = Center
        align = 0 if self.combo_taskbar_pos.currentIndex() == 0 else 1
        black = self.chk_black_taskbar.isChecked()
        return debloat_windows.apply_registry_changes(interactive=False, taskbar_alignment=align, apply_black_taskbar=black)

    # ---------- Data sources ----------
    def get_all_optimizations(self) -> List[Tuple[str, Callable[[], bool]]]:
        return [
            ("Driver Debloat & Settings (AMD)", debloat_windows.run_driver_debloat_settings_amd),
            ("AMD Settings", debloat_windows.apply_amdoptimization),
            ("Timer Resolution", debloat_windows.install_timerresolution),
            ("Start Menu Optimization", debloat_windows.run_startmenuoptimization),
            ("Spectre/Meltdown Optimization", debloat_windows.run_spectre_meltdown),
            ("Uninstall Copilot", debloat_windows.run_copilotuninstaller),
            ("Uninstall Widgets", debloat_windows.run_widgetsuninstaller),
            ("GameBar Optimization", debloat_windows.run_gamebaroptimization),
            ("Configure Power Plan", debloat_windows.apply_powerplan),
            ("Network Optimization", debloat_windows.apply_networkoptimization),
            ("MSI Mode", debloat_windows.apply_msimode),
            ("DirectX Installation", debloat_windows.run_directxinstallation),
            ("C++ Redistributables", debloat_windows.run_cinstallation),
            ("Registry Changes (Apply Config Above)", self.run_registry_changes_gui),
            ("UAC Optimization", debloat_windows.run_uac_optimization),
            ("Core Isolation Optimization", debloat_windows.run_core_isolation_optimization),
            ("Defender Optimize", debloat_windows.run_defender_optimize),
            ("Lock Screen Optimization", debloat_windows.apply_signoutlockscreen),
            ("Uninstall Edge", debloat_windows.run_edgeuninstaller),
            ("Background Apps Optimization", debloat_windows.run_backgroundapps),
            ("Autoruns Optimization", debloat_windows.run_autoruns),
        ]

    def get_all_cleanup(self) -> List[Tuple[str, Callable[[], bool]]]:
        return [
            ("Advanced System Cleanup", debloat_windows.run_advanced_cleanup),
            ("Disable Folder Discovery", debloat_windows.disable_folder_discovery),
            ("Disable WPBT", debloat_windows.disable_wpbt),
        ]

    def get_all_final_steps(self) -> List[Tuple[str, Callable[[], bool]]]:
        return [
            ("Finalize Installation", debloat_windows.finalize_installation),
        ]

    def get_all_others(self) -> List[Tuple[str, Callable[[], bool]]]:
        return [
            ("Run External Debloat Scripts", debloat_windows.run_external_debloat_scripts),
        ]

    def build_cleanup_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(15, 15, 15, 15)
        data = self.get_all_cleanup()
        section = self.build_checklist_section("cleanup", "System Cleanup", data)
        v.addWidget(section)
        return page

    def build_final_steps_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(15, 15, 15, 15)
        data = self.get_all_final_steps()
        section = self.build_checklist_section("final_steps", "Final Steps", data)
        v.addWidget(section)
        return page

    def build_others_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setContentsMargins(15, 15, 15, 15)
        data = self.get_all_others()
        section = self.build_checklist_section("others", "Other Tools", data)
        v.addWidget(section)
        return page



    # ---------- Actions ----------
    def on_menu_changed(self, index: int):
        # Smooth fade transition
        self.page_animation.stop()
        self.page_animation.setStartValue(0.3)
        self.page_animation.setEndValue(1.0)
        self.pages.setCurrentIndex(index)
        self.page_animation.start()
        
        # Mostrar System Info automáticamente al entrar por primera vez
        if index == 6 and not self._info_shown:
            self._info_shown = True
            QTimer.singleShot(250, self.show_system_info)  # Delay for smooth animation

    def set_checks(self, key: str, state: bool):
        for cb in self._checkboxes.get(key, []):
            cb.setChecked(state)
        status = "selected" if state else "cleared"
        self.append_log(f"All items {status} in {key}")

    def run_selected(self, key: str):
        selected: List[Tuple[str, Callable[[], bool]]] = []
        for cb in self._checkboxes.get(key, []):
            if cb.isChecked():
                func = cb.property("task_func")
                if callable(func):
                    selected.append((cb.text(), func))

        if not selected:
            QMessageBox.information(self, "No Tasks Selected", 
                                   "Please select at least one task to run.")
            return

        # Confirmation dialog
        reply = QMessageBox.question(
            self, 
            'Confirm Execution',
            f'You are about to run {len(selected)} task(s).\n\n'
            'This may take several minutes. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            self.append_log("Operation cancelled by user")
            return

        # Prehook para chequeo de conectividad una sola vez
        prehook = None
        if not self._connectivity_checked:
            def _do_check_once():
                try:
                    debloat_windows.test_connectivity()
                finally:
                    self._connectivity_checked = True
            prehook = _do_check_once

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected))

        batch = BatchWorker(selected, prehook=prehook)
        batch.signals.progress.connect(self.append_log)
        batch.signals.progress.connect(lambda: self.progress_bar.setValue(self.progress_bar.value() + 1))
        batch.signals.error.connect(self.on_task_error)
        batch.signals.finished.connect(self.on_batch_finished)

        self.statusBar().showMessage(f"Running {len(selected)} task(s)...")
        self.append_log(f"\n{'='*60}")
        self.append_log(f"Starting batch execution: {len(selected)} task(s)")
        self.append_log(f"{'='*60}\n")
        self.thread_pool.start(batch)

    def on_batch_finished(self, ok: bool, summary: str):
        self.progress_bar.setVisible(False)
        self.append_log(f"\n{'='*60}")
        self.append_log(f"Batch execution completed: {summary}")
        self.append_log(f"{'='*60}\n")
        self.statusBar().showMessage(f"Batch finished: {summary}", 5000)
        
        QMessageBox.information(
            self,
            "Batch Completed",
            f"Batch execution finished!\n\n{summary}\n\n"
            "Check the logs for detailed information."
        )

    def append_log(self, text: str):
        # Optimized logging with batching for better performance
        text = text.rstrip()
        if text:
            self.log_box.appendPlainText(text)
            # Limit log size to prevent memory issues (keep last 5000 lines)
            if self.log_box.document().lineCount() > 5000:
                cursor = self.log_box.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.movePosition(cursor.Down, cursor.KeepAnchor, 500)
                cursor.removeSelectedText()
            # Auto-scroll to bottom (throttled)
            QTimer.singleShot(50, lambda: self.log_box.verticalScrollBar().setValue(
                self.log_box.verticalScrollBar().maximum()
            ))
    
    def clear_logs(self):
        reply = QMessageBox.question(
            self, 
            'Clear Logs',
            'Are you sure you want to clear all logs?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.log_box.clear()
            self.append_log("Logs cleared")

    def on_task_error(self, name: str, err: str):
        self.append_log(f"ERROR in {name}: {err}")
        # Don't show popup for every error, just log it

    def open_app_installer_ps(self):
        """Open the application installer PowerShell script"""
        ps_script = os.path.join(ROOT_DIR, "src", "scripts", "appinstallers.ps1")
        
        if not os.path.exists(ps_script):
            # Try to download it
            self.append_log("Script not found locally, attempting to download...")
            try:
                import requests
                script_url = "https://raw.githubusercontent.com/sogik/ZTalon/refs/heads/main/src/scripts/appinstallers.ps1"
                response = requests.get(script_url, timeout=30)
                
                if response.status_code == 200:
                    os.makedirs(os.path.dirname(ps_script), exist_ok=True)
                    with open(ps_script, "wb") as f:
                        f.write(response.content)
                    self.append_log("Script downloaded successfully")
                else:
                    QMessageBox.warning(
                        self, 
                        "Download Failed",
                        f"Could not download installer script.\n\nHTTP Status: {response.status_code}"
                    )
                    return
            except Exception as e:
                QMessageBox.warning(
                    self, 
                    "Download Error", 
                    f"Error downloading script:\n\n{str(e)}"
                )
                return
        
        try:
            self.append_log(f"Launching Application Installer...")
            self.append_log(f"Script: {ps_script}")
            
            CREATE_NEW_CONSOLE = 0x00000010
            subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_script],
                creationflags=CREATE_NEW_CONSOLE
            )
            self.append_log("Application Installer window opened")
            QMessageBox.information(
                self,
                "Installer Launched",
                "Application Installer has been opened in a new PowerShell window.\n\n"
                "Follow the instructions in that window to install applications."
            )
        except Exception as e:
            self.on_task_error("App Installer", str(e))
            QMessageBox.critical(
                self,
                "Launch Error",
                f"Failed to launch Application Installer:\n\n{str(e)}"
            )

    def build_info_page(self):
        """Build the System Information page"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("System Information")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Info display area (Rich text)
        self.info_text = QTextBrowser()
        self.info_text.setOpenExternalLinks(True)
        self.info_text.setStyleSheet("""
            QTextBrowser {
                background-color: #181825;
                border: 2px solid #313244;
                border-radius: 8px;
                padding: 15px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                line-height: 1.6;
            }
        """)
        layout.addWidget(self.info_text)
        
        # Actions bar
        actions_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh Info")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.show_system_info)
        
        actions_layout.addWidget(refresh_btn)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)
        
        # Initial load
        QTimer.singleShot(500, self.show_system_info)
        
        return page

    def show_system_info(self):
        """Display comprehensive system information with loading indicator"""
        self.append_log("Gathering system information...")
        self.info_text.setHtml("<h3 style='color: #89b4fa;'>⏳ Loading system information...</h3>")
        
        # Run in background thread for better performance
        def gather_info():
            try:
                info = get_system_info()
                
                # Format system info for display using HTML
                html = """
                <style>
                    h3 { color: #89b4fa; margin-bottom: 10px; font-family: 'Segoe UI', sans-serif; }
                    .label { color: #cdd6f4; font-weight: bold; }
                    .value { color: #bac2de; }
                    .section { margin-bottom: 20px; border-bottom: 1px solid #313244; padding-bottom: 10px; }
                </style>
                """
                
                # Operating System
                if 'os' in info:
                    html += "<div class='section'>"
                    html += "<h3>OPERATING SYSTEM</h3>"
                    html += f"<span class='label'>Platform:</span> <span class='value'>{info['os'].get('platform', 'Unknown')}</span><br>"
                    html += f"<span class='label'>Architecture:</span> <span class='value'>{info['os'].get('architecture', ['Unknown'])[0]}</span><br>"
                    html += f"<span class='label'>Version:</span> <span class='value'>{info['os'].get('version', 'Unknown')}</span>"
                    html += "</div>"
                
                # Python
                if 'python' in info:
                    html += "<div class='section'>"
                    html += "<h3>PYTHON ENVIRONMENT</h3>"
                    html += f"<span class='label'>Version:</span> <span class='value'>{info['python'].get('version', 'Unknown')}</span><br>"
                    html += f"<span class='label'>Implementation:</span> <span class='value'>{info['python'].get('implementation', 'Unknown')}</span>"
                    html += "</div>"
                
                # System Resources
                if 'system' in info:
                    html += "<div class='section'>"
                    html += "<h3>SYSTEM RESOURCES</h3>"
                    html += f"<span class='label'>CPU Cores:</span> <span class='value'>{info['system'].get('cpu_count', 'Unknown')}</span><br>"
                    html += f"<span class='label'>Memory:</span> <span class='value'>{info['system'].get('memory_gb', 'Unknown')} GB</span><br>"
                    html += f"<span class='label'>Free Disk Space:</span> <span class='value'>{info['system'].get('disk_free_gb', 'Unknown')} GB</span>"
                    html += "</div>"
                
                # ZTalon Status
                if 'ztalon' in info:
                    html += "<div class='section'>"
                    html += "<h3>ZTALON STATUS</h3>"
                    admin_status = "<span style='color: #a6e3a1;'>Yes</span>" if info['ztalon'].get('admin_privileges') else "<span style='color: #f38ba8;'>No</span>"
                    html += f"<span class='label'>Admin Privileges:</span> {admin_status}<br>"
                    html += f"<span class='label'>Temp Directory:</span> <span class='value'>{info['ztalon'].get('temp_dir', 'Unknown')}</span><br>"
                    ssl_status = "<span style='color: #a6e3a1;'>Enhanced</span>" if info['ztalon'].get('ssl_support') else "<span style='color: #f9e2af;'>Basic</span>"
                    html += f"<span class='label'>SSL Support:</span> {ssl_status}"
                    html += "</div>"
                
                # GPU Information
                try:
                    gpu_info = debloat_windows.get_gpu_info_advanced()
                    html += "<div class='section' style='border: none;'>"
                    html += "<h3>GPU INFORMATION</h3>"
                    if gpu_info and len(gpu_info) > 0:
                        for i, gpu in enumerate(gpu_info, 1):
                            if isinstance(gpu, dict):
                                html += f"<div style='margin-bottom: 8px;'>"
                                html += f"<span class='label'>GPU {i}:</span> <span class='value' style='color: #f9e2af;'>{gpu.get('name', 'Unknown')}</span><br>"
                                html += f"&nbsp;&nbsp;<span class='label'>Type:</span> <span class='value'>{gpu.get('type', 'Unknown')}</span><br>"
                                html += f"&nbsp;&nbsp;<span class='label'>Driver:</span> <span class='value'>{gpu.get('driver_version', 'Unknown')}</span>"
                                html += "</div>"
                            else:
                                html += f"<span class='label'>GPU {i}:</span> <span class='value'>{str(gpu)}</span><br>"
                    else:
                        html += "<span class='value'>No GPU detected</span>"
                    html += "</div>"
                except Exception as e:
                    html += f"<span style='color: #f38ba8;'>Error detecting GPU: {str(e)}</span>"
                
                return True, html
            except Exception as e:
                return False, f"<h3 style='color: #f38ba8;'>Error gathering system information: {e}</h3>"
        
        def on_info_complete(ok, text):
            if ok:
                self.info_text.setHtml(text)
                self.append_log("System information updated")
            else:
                self.info_text.setHtml(text)
                self.append_log("Failed to gather system information")
        
        worker = Worker("System Info", gather_info)
        worker.signals.finished.connect(lambda ok, name: on_info_complete(ok, gather_info()[1]))
        self.thread_pool.start(worker)
    
    def run_system_checks(self):
        """Run comprehensive system checks"""
        self.append_log("\n" + "="*60)
        self.append_log("Running system compatibility checks...")
        self.append_log("="*60 + "\n")
        
        try:
            # Check Windows version
            self.append_log("Checking Windows version...")
            try:
                reg = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
                key = winreg.OpenKey(reg, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                
                product_name, _ = winreg.QueryValueEx(key, "ProductName")
                build_number, _ = winreg.QueryValueEx(key, "CurrentBuildNumber")
                
                winreg.CloseKey(key)
                winreg.CloseKey(reg)
                
                self.append_log(f"   OS: {product_name}")
                self.append_log(f"   Build: {build_number}")
                
                if int(build_number) >= 19041:
                    self.append_log("   Windows version supported")
                else:
                    self.append_log("   WARNING: Windows version may not be fully supported")
            except Exception as e:
                self.append_log(f"   ERROR checking Windows version: {e}")
            
            # Check admin privileges
            self.append_log("\nChecking administrator privileges...")
            if check_admin_privileges():
                self.append_log("   Running with administrator privileges")
            else:
                self.append_log("   WARNING: Not running as administrator - some features may be limited")
            
            # Check temp directory
            self.append_log("\nChecking temp directory...")
            temp_dir = tempfile.gettempdir()
            self.append_log(f"   Location: {temp_dir}")
            if os.path.exists(temp_dir) and os.access(temp_dir, os.W_OK):
                self.append_log("   Temp directory is writable")
            else:
                self.append_log("   ERROR: Temp directory is not writable")
            
            # Check internet connectivity
            self.append_log("\nChecking internet connectivity...")
            try:
                import socket
                socket.create_connection(("8.8.8.8", 53), timeout=3)
                self.append_log("   Internet connection active")
            except OSError:
                self.append_log("   ERROR: No internet connection detected")
            
            self.append_log("\n" + "="*60)
            self.append_log("System checks completed")
            self.append_log("="*60 + "\n")
            
            QMessageBox.information(
                self,
                "System Checks Complete",
                "System compatibility checks completed.\n\nCheck the logs for detailed results."
            )
            
        except Exception as e:
            self.append_log(f"ERROR during system checks: {e}")
            QMessageBox.critical(
                self,
                "Check Failed",
                f"System checks encountered an error:\n\n{str(e)}"
            )
    
    def restart_computer(self):
        """Restart the computer with confirmation"""
        reply = QMessageBox.question(
            self,
            'Restart Computer',
            'Are you sure you want to restart your computer?\n\n'
            'Make sure to save all your work before continuing.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.append_log("Initiating system restart...")
                subprocess.run(["shutdown", "/r", "/t", "10"], check=True)
                self.append_log("System will restart in 10 seconds")
                QMessageBox.information(
                    self,
                    "Restart Scheduled",
                    "Your computer will restart in 10 seconds.\n\n"
                    "To cancel, run: shutdown /a"
                )
            except Exception as e:
                self.append_log(f"Failed to restart: {e}")
                QMessageBox.critical(
                    self,
                    "Restart Failed",
                    f"Could not restart computer:\n\n{str(e)}\n\n"
                    "Please restart manually."
                )

    def install_logging_bridge(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        for h in list(root_logger.handlers):
            if isinstance(h, QtLogHandler):
                root_logger.removeHandler(h)
        qt_handler = QtLogHandler(self.log_bridge)
        qt_handler.setLevel(logging.INFO)
        qt_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        root_logger.addHandler(qt_handler)


def main():
    # Enable high DPI scaling for better display on modern monitors
    # Must be set BEFORE QApplication is created
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    # Set app metadata
    app.setApplicationName("ZTalon")
    app.setApplicationVersion("1.0.1")
    app.setOrganizationName("sogik Development")
    
    try:
        # Create and show main window
        win = ZTalonGUI()
        win.show()
        
        # Display welcome message after window loads
        QTimer.singleShot(100, lambda: win.append_log("✅ ZTalon GUI loaded successfully"))
        QTimer.singleShot(200, lambda: win.append_log("Select a section from the menu to get started"))
        
        sys.exit(app.exec_())
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
