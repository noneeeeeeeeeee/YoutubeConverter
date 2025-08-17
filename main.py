import os
import sys
import signal
from typing import List, Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QFileDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QFrame,
)

from core.settings import SettingsManager, AppSettings
from core.ffmpeg_manager import FfmpegInstaller, ensure_ffmpeg_in_path
from core.yt_manager import YtDlpUpdateWorker, AppUpdateWorker
from ui.style import StyleManager
from ui.stepper import Stepper
from ui.toast import ToastManager
from widgets.step1_link import Step1LinkWidget
from widgets.step2_playlist import Step2PlaylistWidget
from widgets.step3_quality import Step3QualityWidget
from widgets.step4_downloads import Step4DownloadsWidget

APP_VERSION = "0.1.0"
APP_REPO = "noneeeeeeeeeee/YoutubeConverter"  # repository to check for updates


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Converter")
        self.setMinimumSize(1024, 640)
        self.settings_mgr = SettingsManager()
        self.settings: AppSettings = self.settings_mgr.load()

        # Style
        self.style_mgr = StyleManager(self.settings.ui.accent_color_hex)
        self.setStyleSheet(self.style_mgr.qss())
        self.toast = ToastManager(self)

        # Left sidebar (Home, Settings)
        self.sidebar = self._build_sidebar()
        # Top stepper
        self.stepper = Stepper()
        # Central stack of step widgets
        self.stack = QStackedWidget()
        self._build_pages()

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        root_layout.addWidget(self.sidebar)

        # Right area: top stepper + stack
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)
        right_layout.addWidget(self.stepper)
        right_layout.addWidget(self.stack, 1)
        root_layout.addWidget(right, 1)

        self.setCentralWidget(root)

        # Signals wiring
        self._wire_signals()

        # FFmpeg ensure
        self._ensure_ffmpeg()

        # yt-dlp auto update
        if self.settings.ytdlp.auto_update:
            self._check_ytdlp_updates()

        # App auto update on launch
        if self.settings.app.auto_update:
            self._check_app_updates(check_only=False)

        # Initialize steps display
        self._refresh_stepper_titles(is_playlist=False)

    def _build_sidebar(self) -> QWidget:
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(64)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        self.btn_home = QPushButton("🏠")
        self.btn_home.setToolTip("Home")
        self.btn_home.setObjectName("IconButton")
        self.btn_home.setFixedSize(48, 48)
        # Remove focus outline on icon buttons
        self.btn_home.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_settings = QPushButton("⚙️")
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.setObjectName("IconButton")
        self.btn_settings.setFixedSize(48, 48)
        self.btn_settings.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        lay.addWidget(self.btn_home)
        lay.addWidget(self.btn_settings)
        lay.addStretch(1)
        return side

    def _build_pages(self):
        # Home flow widgets
        self.page_flow = QWidget()
        flow_layout = QVBoxLayout(self.page_flow)
        flow_layout.setContentsMargins(0, 0, 0, 0)
        flow_layout.setSpacing(0)

        self.step1 = Step1LinkWidget(self.settings)
        self.step2 = Step2PlaylistWidget()
        self.step3 = Step3QualityWidget(self.settings)
        self.step4 = Step4DownloadsWidget(self.settings)

        self.flow_stack = QStackedWidget()
        self.flow_stack.addWidget(self.step1)  # index 0
        self.flow_stack.addWidget(self.step2)  # index 1 (playlist select)
        self.flow_stack.addWidget(self.step3)  # index 2 (quality)
        self.flow_stack.addWidget(self.step4)  # index 3 (downloads)

        flow_layout.addWidget(self.flow_stack)

        # Settings page
        self.page_settings = self._build_settings_page()

        self.stack.addWidget(self.page_flow)  # index 0
        self.stack.addWidget(self.page_settings)  # index 1

    def _build_settings_page(self) -> QWidget:
        from PyQt6.QtWidgets import (
            QFormLayout,
            QCheckBox,
            QComboBox,
            QColorDialog,
            QLineEdit,
        )

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Auto-advance
        self.chk_auto_advance = QCheckBox()
        self.chk_auto_advance.setChecked(self.settings.ui.auto_advance)
        form.addRow("Auto-advance", self.chk_auto_advance)

        # Accent color
        self.btn_accent = QPushButton("Pick accent color")
        self.btn_accent.clicked.connect(self._pick_accent)
        form.addRow("Accent color", self.btn_accent)

        # yt-dlp updates
        self.chk_ytdlp_auto = QCheckBox()
        self.chk_ytdlp_auto.setChecked(self.settings.ytdlp.auto_update)
        form.addRow("Auto-update yt-dlp", self.chk_ytdlp_auto)

        self.cmb_ytdlp_branch = QComboBox()
        self.cmb_ytdlp_branch.addItems(["stable", "nightly", "master"])
        self.cmb_ytdlp_branch.setCurrentText(self.settings.ytdlp.branch)
        form.addRow("yt-dlp branch", self.cmb_ytdlp_branch)

        self.btn_ytdlp_check = QPushButton("Check yt-dlp now")
        self.btn_ytdlp_check.clicked.connect(self._check_ytdlp_updates)
        form.addRow("", self.btn_ytdlp_check)

        # App updates
        self.chk_app_auto = QCheckBox()
        self.chk_app_auto.setChecked(self.settings.app.auto_update)
        form.addRow("Auto-update app", self.chk_app_auto)

        self.cmb_app_channel = QComboBox()
        self.cmb_app_channel.addItems(["release", "prerelease"])
        self.cmb_app_channel.setCurrentText(self.settings.app.channel)
        form.addRow("App update channel", self.cmb_app_channel)

        self.btn_app_check = QPushButton("Check app update")
        self.btn_app_check.clicked.connect(
            lambda: self._check_app_updates(check_only=True)
        )
        form.addRow("", self.btn_app_check)

        lay.addLayout(form)

        # Auto-save handlers (remove explicit Save button)
        self.chk_auto_advance.toggled.connect(self._settings_changed)
        self.chk_ytdlp_auto.toggled.connect(self._settings_changed)
        self.cmb_ytdlp_branch.currentTextChanged.connect(self._settings_changed)
        self.chk_app_auto.toggled.connect(self._settings_changed)
        self.cmb_app_channel.currentTextChanged.connect(self._settings_changed)

        return page

    def _wire_signals(self):
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        # Step 1
        self.step1.urlDetected.connect(self._on_url_detected)
        self.step1.requestAdvance.connect(self._advance_from_step1)

        # Step 2
        self.step2.selectionConfirmed.connect(self._advance_from_step2)
        self.step2.backRequested.connect(self._back_from_step2)

        # Step 3
        self.step3.qualityConfirmed.connect(self._advance_from_step3)
        self.step3.backRequested.connect(self._back_from_step3)

        # Step 4
        self.step4.allFinished.connect(self._on_downloads_finished)
        self.step4.backRequested.connect(self._back_from_step4)

    def _refresh_stepper_titles(self, is_playlist: bool):
        if is_playlist:
            self.stepper.set_steps(["Link", "Select", "Quality", "Download"])
        else:
            self.stepper.set_steps(["Link", "Quality", "Download"])
        self.stepper.set_current(0)

    def _on_url_detected(self, info: Dict):
        is_playlist = info.get("_type") == "playlist" or info.get("entries") is not None
        self._refresh_stepper_titles(is_playlist)

    def _advance_from_step1(self, payload: Dict):
        # payload: {"url": str, "info": dict, "is_playlist": bool}
        is_playlist = payload.get("is_playlist", False)
        info = payload.get("info", {})
        self.step4.reset()  # clear old list
        if is_playlist:
            # Fill playlist selection
            self.step2.set_entries(info.get("entries") or [])
            self.flow_stack.setCurrentIndex(1)
            self.stepper.set_current(1)
        else:
            # Single video -> go to quality
            self.step3.set_items([info])
            self.flow_stack.setCurrentIndex(2)
            self.stepper.set_current(1)
        self.stack.setCurrentIndex(0)

    def _advance_from_step2(self, entries: List[Dict]):
        # entries selected from playlist -> to quality
        if not entries:
            self.toast.show("No videos selected from playlist.")
            return
        self.step3.set_items(entries)
        self.flow_stack.setCurrentIndex(2)
        self.stepper.set_current(2)

    def _advance_from_step3(self, selection: Dict):
        # selection: {"items": [...], "kind": "audio"/"video", "format": "...", "quality": "..."
        items = selection.get("items", [])
        if not items:
            return
        self.step4.configure(selection, self.settings)
        self.flow_stack.setCurrentIndex(3)
        # Step index depends on playlist vs single
        is_playlist = len(items) > 1
        self.stepper.set_current(3 if is_playlist else 2)
        # Do NOT auto-start here

    def _on_downloads_finished(self):
        if self.settings.ui.reset_after_downloads:
            # Reset to step 1
            self.flow_stack.setCurrentIndex(0)
            self.stepper.set_current(0)
            self.step1.reset()
        else:
            # Switch button to Done already managed in step4 widget; stay on page
            pass

    def _pick_accent(self):
        from PyQt6.QtWidgets import QColorDialog

        c = QColorDialog.getColor()
        if c.isValid():
            self.settings.ui.accent_color_hex = c.name()
            self.setStyleSheet(self.style_mgr.with_accent(c.name()))
            self._settings_changed()
            self.toast.show(f"Accent changed to {c.name()}")

    def _settings_changed(self):
        # Persist changes immediately
        self.settings.ui.auto_advance = self.chk_auto_advance.isChecked()
        self.settings.ytdlp.auto_update = self.chk_ytdlp_auto.isChecked()
        self.settings.ytdlp.branch = self.cmb_ytdlp_branch.currentText()
        self.settings.app.auto_update = self.chk_app_auto.isChecked()
        self.settings.app.channel = self.cmb_app_channel.currentText()
        self.settings_mgr.save(self.settings)
        # No toast spam here

    def _ensure_ffmpeg(self):
        ok = ensure_ffmpeg_in_path()
        if ok:
            return
        self.toast.show("FFmpeg not found. Downloading...")
        self.ff_thread = FfmpegInstaller(self)
        self.ff_thread.progress.connect(
            lambda p: self.toast.show(f"Downloading FFmpeg... {p}%")
        )
        self.ff_thread.finished_ok.connect(lambda path: self.toast.show("FFmpeg ready"))
        self.ff_thread.finished_fail.connect(
            lambda e: self.toast.show(f"FFmpeg install failed: {e}")
        )
        self.ff_thread.start()

    def _check_ytdlp_updates(self):
        self.toast.show("Checking for yt-dlp updates...")
        self.yt_thread = YtDlpUpdateWorker(self.settings.ytdlp.branch, check_only=True)
        self.yt_thread.status.connect(lambda s: self.toast.show(s))
        if self.settings.ytdlp.auto_update:
            # perform update
            self.yt_thread.check_only = False
        self.yt_thread.finished.connect(lambda: None)
        self.yt_thread.start()

    def _check_app_updates(self, check_only: bool = False):
        do_update = not check_only and self.settings.app.auto_update
        channel = self.settings.app.channel
        self.toast.show("Checking app updates...")
        self.app_up_thread = AppUpdateWorker(APP_REPO, channel, APP_VERSION, do_update)
        self.app_up_thread.status.connect(lambda s: self.toast.show(s))

        def _after(updated: bool):
            if updated:
                self.toast.show("Restarting to finish update...")
                # Restart app
                python = sys.executable
                os.execv(python, [python] + sys.argv)

        self.app_up_thread.updated.connect(_after)
        self.app_up_thread.start()

    def _back_from_step2(self):
        self.flow_stack.setCurrentIndex(0)
        self.stepper.set_current(0)

    def _back_from_step3(self):
        is_playlist = len(self.stepper._labels) == 4
        self.flow_stack.setCurrentIndex(1 if is_playlist else 0)
        self.stepper.set_current(1 if is_playlist else 0)

    def _back_from_step4(self):
        self.flow_stack.setCurrentIndex(2)
        is_playlist = len(self.stepper._labels) == 4
        self.stepper.set_current(2 if is_playlist else 1)


def main():
    # Better SIGINT handling on Windows consoles
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    # Guard high-DPI attributes (may not exist in Qt6)
    try:
        if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
            app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
            app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    except Exception:
        pass
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
