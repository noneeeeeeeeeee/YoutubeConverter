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
    QScrollArea,  # added
)


def _app_dir() -> str:
    # Prefer the executable directory when frozen
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


try:
    import certifi

    local_ca = os.path.join(_app_dir(), "cacert.pem")
    ca_path = local_ca if os.path.isfile(local_ca) else certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", ca_path)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_path)
except Exception:
    pass

from core.settings import SettingsManager, AppSettings
from core.ffmpeg_manager import FfmpegInstaller, ensure_ffmpeg_in_path
from core.update import YtDlpUpdateWorker, AppUpdateWorker  # CHANGED: moved here
from core.yt_manager import InfoFetcher  # kept
from ui.style import StyleManager
from ui.stepper import Stepper
from ui.toast import ToastManager
from widgets.step1_link import Step1LinkWidget
from widgets.step3_quality import Step3QualityWidget
from widgets.step4_downloads import Step4DownloadsWidget
from widgets.settings_page import SettingsPage


def _read_version_from_file() -> str:
    try:
        ver_path = os.path.join(_app_dir(), "version.txt")
        if os.path.exists(ver_path):
            with open(ver_path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception:
        pass
    return ""


APP_VERSION = _read_version_from_file() or "Unknown"
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

        self._bg_fetcher = None  # background fetcher for fast-add on downloads

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
        self.settings_page = SettingsPage(self.settings)  # inner widget

        # Make settings scrollable
        self.settings_scroll = QScrollArea()
        self.settings_scroll.setWidgetResizable(True)
        self.settings_scroll.setObjectName("SettingsScrollArea")
        self.settings_scroll.setWidget(self.settings_page)
        # Flatten look: remove border/frame, keep scrollbar
        self.settings_scroll.setFrameShape(QFrame.Shape.NoFrame)  # NEW
        self.settings_scroll.setStyleSheet(  # NEW
            "QScrollArea { border: none; background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        self.stack.addWidget(self.page_flow)
        self.stack.addWidget(
            self.settings_scroll
        )  # add scroll area instead of raw page

    def _wire_signals(self):
        self.btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        # Step 1
        self.step1.urlDetected.connect(lambda _: self._refresh_stepper_titles())
        self.step1.requestAdvance.connect(self._advance_single_from_step1)
        self.step1.selectionConfirmed.connect(self._advance_multi_from_step1)

        # Step 2
        self.step3.qualityConfirmed.connect(self._advance_from_step3)
        self.step3.backRequested.connect(
            lambda: (self.flow_stack.setCurrentIndex(0), self.stepper.set_current(0))
        )

        # Step 3
        self.step4.allFinished.connect(self._on_downloads_finished)
        self.step4.backRequested.connect(
            lambda: (self.flow_stack.setCurrentIndex(1), self.stepper.set_current(1))
        )

        # Settings page signals (connect on inner widget)
        self.settings_page.changed.connect(self._settings_changed)  # NEW
        self.settings_page.accentPickRequested.connect(self._pick_accent)  # NEW
        self.settings_page.checkYtDlpRequested.connect(self._check_ytdlp_updates)  # NEW
        self.settings_page.checkAppCheckOnlyRequested.connect(
            lambda: self._check_app_updates(check_only=True)
        )

    def _refresh_stepper_titles(self):
        self.stepper.set_steps(["Select", "Quality", "Download"])
        self.stepper.set_current(0)

    def _on_url_detected(self, info: Dict):
        is_playlist = info.get("_type") == "playlist" or info.get("entries") is not None
        self._refresh_stepper_titles()

    def _advance_single_from_step1(self, payload: Dict):
        info = payload.get("info") or {}
        if not info:
            return
        # If already on downloads page, do not go back to Step 2
        if self.flow_stack.currentIndex() == 2:
            url = payload.get("url") or info.get("webpage_url") or info.get("url")
            if not url:
                return
            # Fetch full metadata before adding
            self.toast.show("Fetching video info...")
            self._bg_fetcher = InfoFetcher(url)

            def _ok(meta):
                # Build default selection (use user's defaults; quality best)
                kind = self.settings.defaults.kind or "audio"
                fmt = self.settings.defaults.format if kind == "audio" else "mp4"
                selection = {
                    "items": [meta],
                    "kind": kind,
                    "format": fmt,
                    "quality": "best",
                }
                self.step4.configure(selection, self.settings)
                self.toast.show("Added to downloads.")

            def _fail(err):
                self.toast.show(f"Failed to fetch info: {err}")

            self._bg_fetcher.finished_ok.connect(_ok)
            self._bg_fetcher.finished_fail.connect(_fail)
            self._bg_fetcher.start()
            return

        # Normal path: go to Step 2 for quality selection
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

    def _on_downloads_finished(self):
        # Always clear Step 1 contents after downloads
        self.step1.reset()
        if self.settings.ui.reset_after_downloads:
            # Reset to step 1
            self.flow_stack.setCurrentIndex(0)
            self.stepper.set_current(0)
        else:
            # Stay on downloads page; Step 1 is already cleared
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
        # Persist changes immediately using SettingsPage
        self.settings_page.apply_to(self.settings)
        self.settings_mgr.save(self.settings)

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
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
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
