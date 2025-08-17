import os
import sys
import signal
from typing import List, Dict
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStackedWidget,
    QPushButton,
    QFrame,
    QGroupBox,
    QSpinBox,
)

from core.settings import SettingsManager, AppSettings
from core.ffmpeg_manager import FfmpegInstaller, ensure_ffmpeg_in_path
from core.yt_manager import YtDlpUpdateWorker, AppUpdateWorker
from ui.style import StyleManager
from ui.stepper import Stepper
from ui.toast import ToastManager
from widgets.step1_link import Step1LinkWidget
from widgets.step3_quality import Step3QualityWidget
from widgets.step4_downloads import Step4DownloadsWidget

APP_VERSION = "0.1-Beta"
APP_REPO = "noneeeeeeeeeee/YoutubeConverter"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"YouTube Converter {APP_VERSION}")
        self.setMinimumSize(1024, 640)
        self.settings_mgr = SettingsManager()
        self.settings: AppSettings = self.settings_mgr.load()

        self.style_mgr = StyleManager(self.settings.ui.accent_color_hex)
        self.setStyleSheet(self.style_mgr.qss())
        self.toast = ToastManager(self)

        self.sidebar = self._build_sidebar()
        self.stepper = Stepper()
        self.stack = QStackedWidget()
        self._build_pages()

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self.sidebar)

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
        self._refresh_stepper_titles()

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
        self.page_flow = QWidget()
        flow_layout = QVBoxLayout(self.page_flow)
        flow_layout.setContentsMargins(0, 0, 0, 0)
        flow_layout.setSpacing(0)

        self.step1 = Step1LinkWidget(self.settings)
        self.step3 = Step3QualityWidget(self.settings)
        self.step4 = Step4DownloadsWidget(self.settings)

        self.flow_stack = QStackedWidget()
        self.flow_stack.addWidget(self.step1)
        self.flow_stack.addWidget(self.step3)
        self.flow_stack.addWidget(self.step4)

        flow_layout.addWidget(self.flow_stack)

        # Settings page
        self.page_settings = self._build_settings_page()

        self.stack.addWidget(self.page_flow)
        self.stack.addWidget(self.page_settings)

    def _build_settings_page(self) -> QWidget:
        from PyQt6.QtWidgets import QFormLayout, QCheckBox, QComboBox, QColorDialog

        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)

        # General group
        grp_general = QGroupBox("General")
        frm_general = QFormLayout(grp_general)
        frm_general.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.chk_auto_advance = QCheckBox()
        self.chk_auto_advance.setChecked(self.settings.ui.auto_advance)
        frm_general.addRow("Auto-advance", self.chk_auto_advance)

        self.chk_auto_fetch_urls = QCheckBox()
        self.chk_auto_fetch_urls.setChecked(self.settings.ui.auto_fetch_urls)
        frm_general.addRow("Auto fetch URLs", self.chk_auto_fetch_urls)

        self.chk_auto_search_text = QCheckBox()
        self.chk_auto_search_text.setChecked(self.settings.ui.auto_search_text)
        frm_general.addRow("Auto search text", self.chk_auto_search_text)

        # New: live search and debounce seconds
        self.chk_live_search = QCheckBox()
        self.chk_live_search.setChecked(getattr(self.settings.ui, "live_search", True))
        frm_general.addRow("Live search while typing", self.chk_live_search)

        self.spn_search_debounce = QSpinBox()
        self.spn_search_debounce.setRange(0, 10)
        self.spn_search_debounce.setValue(
            int(getattr(self.settings.ui, "search_debounce_seconds", 3))
        )
        frm_general.addRow("Search debounce (s)", self.spn_search_debounce)

        self.chk_clear_after_fetch = QCheckBox()
        self.chk_clear_after_fetch.setChecked(self.settings.ui.clear_input_after_fetch)
        frm_general.addRow("Clear input after fetch", self.chk_clear_after_fetch)

        self.btn_accent = QPushButton("Pick accent color")
        self.btn_accent.clicked.connect(self._pick_accent)
        frm_general.addRow("Accent color", self.btn_accent)

        lay.addWidget(grp_general)

        # yt-dlp group
        grp_ytdlp = QGroupBox("yt-dlp")
        frm_ytdlp = QFormLayout(grp_ytdlp)
        frm_ytdlp.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.chk_ytdlp_auto = QCheckBox()
        self.chk_ytdlp_auto.setChecked(self.settings.ytdlp.auto_update)
        frm_ytdlp.addRow("Auto-update yt-dlp", self.chk_ytdlp_auto)

        self.cmb_ytdlp_branch = QComboBox()
        self.cmb_ytdlp_branch.addItems(["stable", "nightly", "master"])
        self.cmb_ytdlp_branch.setCurrentText(self.settings.ytdlp.branch)
        frm_ytdlp.addRow("yt-dlp branch", self.cmb_ytdlp_branch)

        self.btn_ytdlp_check = QPushButton("Check yt-dlp now")
        self.btn_ytdlp_check.clicked.connect(self._check_ytdlp_updates)
        frm_ytdlp.addRow("", self.btn_ytdlp_check)

        lay.addWidget(grp_ytdlp)

        # App updates group
        grp_app = QGroupBox("App updates")
        frm_app = QFormLayout(grp_app)
        frm_app.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.chk_app_auto = QCheckBox()
        self.chk_app_auto.setChecked(self.settings.app.auto_update)
        frm_app.addRow("Auto-update app", self.chk_app_auto)

        self.cmb_app_channel = QComboBox()
        self.cmb_app_channel.addItems(["release", "prerelease"])
        self.cmb_app_channel.setCurrentText(self.settings.app.channel)
        frm_app.addRow("Update channel", self.cmb_app_channel)

        self.btn_app_check = QPushButton("Check app update")
        self.btn_app_check.clicked.connect(
            lambda: self._check_app_updates(check_only=True)
        )
        frm_app.addRow("", self.btn_app_check)

        lay.addWidget(grp_app)
        lay.addStretch(1)

        # Auto-save handlers
        self.chk_auto_advance.toggled.connect(self._settings_changed)
        self.chk_auto_fetch_urls.toggled.connect(self._settings_changed)
        self.chk_auto_search_text.toggled.connect(self._settings_changed)
        self.chk_live_search.toggled.connect(self._settings_changed)
        self.spn_search_debounce.valueChanged.connect(self._settings_changed)
        self.chk_clear_after_fetch.toggled.connect(self._settings_changed)
        self.chk_ytdlp_auto.toggled.connect(self._settings_changed)
        self.cmb_ytdlp_branch.currentTextChanged.connect(self._settings_changed)
        self.chk_app_auto.toggled.connect(self._settings_changed)
        self.cmb_app_channel.currentTextChanged.connect(self._settings_changed)

        return page

    def _wire_signals(self):
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        # Step 1 (merged)
        self.step1.urlDetected.connect(lambda _: self._refresh_stepper_titles())
        self.step1.requestAdvance.connect(self._advance_single_from_step1)
        self.step1.selectionConfirmed.connect(self._advance_multi_from_step1)

        # Step 3
        self.step3.qualityConfirmed.connect(self._advance_from_step3)
        self.step3.backRequested.connect(
            lambda: (self.flow_stack.setCurrentIndex(0), self.stepper.set_current(0))
        )

        # Step 4
        self.step4.allFinished.connect(self._on_downloads_finished)
        self.step4.backRequested.connect(
            lambda: (self.flow_stack.setCurrentIndex(1), self.stepper.set_current(1))
        )

    def _refresh_stepper_titles(self):
        # Always 3 steps now: Select -> Quality -> Download
        self.stepper.set_steps(["Select", "Quality", "Download"])
        self.stepper.set_current(0)

    def _on_url_detected(self, info: Dict):
        is_playlist = info.get("_type") == "playlist" or info.get("entries") is not None
        self._refresh_stepper_titles()

    def _advance_single_from_step1(self, payload: Dict):
        # Immediate advance with single item
        info = payload.get("info") or {}
        if not info:
            return
        self.step3.set_items([info])
        self.flow_stack.setCurrentIndex(1)
        self.stepper.set_current(1)

    def _advance_multi_from_step1(self, items: List[Dict]):
        if not items:
            return
        self.step3.set_items(items)
        self.flow_stack.setCurrentIndex(1)
        self.stepper.set_current(1)

    def _advance_from_step3(self, selection: Dict):
        # selection: {"items": [...], "kind": "audio"/"video", "format": "...", "quality": "..."
        items = selection.get("items", [])
        if not items:
            return
        self.step4.configure(selection, self.settings)
        self.flow_stack.setCurrentIndex(2)
        self.stepper.set_current(2)
        # User presses Start in step 4

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
        self.settings.ui.auto_fetch_urls = self.chk_auto_fetch_urls.isChecked()
        self.settings.ui.auto_search_text = self.chk_auto_search_text.isChecked()
        self.settings.ui.live_search = self.chk_live_search.isChecked()
        self.settings.ui.search_debounce_seconds = int(self.spn_search_debounce.value())
        self.settings.ui.clear_input_after_fetch = (
            self.chk_clear_after_fetch.isChecked()
        )
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
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
