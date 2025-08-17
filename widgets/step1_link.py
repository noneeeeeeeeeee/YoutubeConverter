import re
from typing import Dict
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
)
from PyQt6.QtGui import QIcon, QPixmap

from core.settings import AppSettings
from core.yt_manager import InfoFetcher

YOUTUBE_URL_RE = re.compile(r"https?://[^\s]+")


class Step1LinkWidget(QWidget):
    urlDetected = pyqtSignal(dict)  # info dict for updating stepper
    requestAdvance = pyqtSignal(dict)  # {"url": str, "info": dict, "is_playlist": bool}

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.fetcher = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        hl = QHBoxLayout()
        self.txt = QLineEdit()
        self.txt.setPlaceholderText(
            "Paste a YouTube URL or type to search, then press Enter…"
        )
        self.btn_primary = QPushButton("Paste")
        hl.addWidget(self.txt, 1)
        hl.addWidget(self.btn_primary)
        lay.addLayout(hl)

        self.results = QListWidget()
        self.results.setIconSize(QSize(96, 54))
        self.results.setVisible(False)
        lay.addWidget(self.results, 1)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(self.lbl_status)

        # Signals
        self.btn_primary.clicked.connect(self._primary_clicked)
        self.results.itemDoubleClicked.connect(self._result_chosen)
        self.txt.returnPressed.connect(self._enter_pressed)
        self.txt.textChanged.connect(self._on_text_change)
        self._update_primary_button()

    def _update_primary_button(self):
        q = self.txt.text().strip()
        if not q:
            self.btn_primary.setText("Paste")
        elif YOUTUBE_URL_RE.match(q):
            self.btn_primary.setText("Fetch")
        else:
            self.btn_primary.setText("Search")

    def _primary_clicked(self):
        q = self.txt.text().strip()
        if not q:
            # Paste
            from PyQt6.QtWidgets import QApplication

            txt = QApplication.clipboard().text().strip()
            if txt:
                self.txt.setText(txt)
                self._update_primary_button()
                if YOUTUBE_URL_RE.match(txt):
                    self._start_fetch(txt)
            return
        if YOUTUBE_URL_RE.match(q):
            self._start_fetch(q)
        else:
            self._start_fetch(f"ytsearch20:{q}")

    def _enter_pressed(self):
        self._primary_clicked()

    def _on_text_change(self, _: str):
        # Toggle button label; Enter triggers action
        self._update_primary_button()

    def _start_fetch(self, url: str):
        if self.fetcher and self.fetcher.isRunning():
            return
        self.lbl_status.setText("Fetching...")
        self.fetcher = InfoFetcher(url)
        self.fetcher.finished_ok.connect(self._info_ok)
        self.fetcher.finished_fail.connect(self._info_fail)
        self.fetcher.start()

    def _result_chosen(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)
        if url:
            self.txt.setText(url)
            self._start_fetch(url)

    def _info_ok(self, info: Dict):
        self.lbl_status.setText("")
        # If search results
        if (
            info.get("_type") == "playlist"
            and info.get("extractor_key") == "YoutubeSearch"
        ):
            self.results.clear()
            for e in info.get("entries", []) or []:
                title = e.get("title") or "Unknown title"
                url = e.get("webpage_url") or ""
                it = QListWidgetItem(title)
                it.setData(Qt.ItemDataRole.UserRole, url)
                # thumbnail icon
                thumb_url = e.get("thumbnail") or (e.get("thumbnails") or [{}])[-1].get(
                    "url"
                )
                pix = self._load_thumb(thumb_url)
                if pix:
                    it.setIcon(QIcon(pix))
                self.results.addItem(it)
            self.results.setVisible(True)
            return

        # Normal link or playlist
        self.results.setVisible(False)
        self.urlDetected.emit(info)
        is_playlist = info.get("_type") == "playlist" or info.get("entries") is not None
        payload = {
            "url": self.txt.text().strip(),
            "info": info,
            "is_playlist": is_playlist,
        }
        # Auto-advance if enabled or after selection (selection handled via double-click)
        if self.settings.ui.auto_advance:
            self.requestAdvance.emit(payload)

    def _info_fail(self, err: str):
        self.lbl_status.setText(f"Error: {err}")

    def _load_thumb(self, url: str):
        if not url:
            return None
        try:
            import requests

            r = requests.get(url, timeout=6)
            if not r.ok:
                return None
            pix = QPixmap()
            if pix.loadFromData(r.content):
                return pix
        except Exception:
            return None
        return None

    def reset(self):
        self.txt.clear()
        self.results.clear()
        self.results.setVisible(False)
        self.lbl_status.setText("")
        self._update_primary_button()
