import os
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
)

from core.settings import AppSettings, SettingsManager
from core.ffmpeg_manager import FF_EXE, FF_DIR
from core.yt_manager import Downloader, InfoFetcher  # add InfoFetcher


class DownloadItemWidget(QWidget):
    def __init__(self, title: str):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(8)

        self.thumb = QLabel()
        self.thumb.setFixedSize(96, 54)
        self.thumb.setStyleSheet(
            "background:#111;border:1px solid #333;border-radius:6px;"
        )
        self.thumb.setScaledContents(True)

        self.title = QLabel(title)
        self.title.setWordWrap(True)

        self.status = QLabel("Waiting...")
        self.progress = QProgressBar()
        self.progress.setValue(0)

        col = QVBoxLayout()
        col.addWidget(self.title)
        col.addWidget(self.status)
        col.addWidget(self.progress)

        lay.addWidget(self.thumb)
        lay.addLayout(col, 1)


class Step4DownloadsWidget(QWidget):
    allFinished = pyqtSignal()
    backRequested = pyqtSignal()

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.settings_mgr = SettingsManager()
        self.items: List[Dict] = []
        self.kind = "audio"
        self.fmt = "mp3"
        self.quality = "best"
        self.downloader: Optional[Downloader] = None
        self._meta_fetchers: dict[int, InfoFetcher] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        top = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.lbl_dir = QLabel(self.settings.last_download_dir)
        self.btn_choose = QPushButton("Choose folder")
        self.btn_start = QPushButton("Start")
        self.btn_start.setEnabled(False)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_done = QPushButton("Done")
        self.btn_done.setVisible(False)
        self.btn_back.clicked.connect(self.backRequested.emit)
        self.btn_choose.clicked.connect(self._choose_dir)
        self.btn_start.clicked.connect(self._toggle_start_pause)
        self.btn_stop.clicked.connect(self._stop_downloads)
        self.btn_done.clicked.connect(self._done_clicked)
        top.addWidget(self.btn_back)
        top.addWidget(QLabel("Save to:"))
        top.addWidget(self.lbl_dir, 1)
        top.addWidget(self.btn_choose)
        top.addWidget(self.btn_start)
        top.addWidget(self.btn_stop)
        top.addWidget(self.btn_done)
        lay.addLayout(top)

        self.list = QListWidget()
        lay.addWidget(self.list, 1)

    def configure(self, selection: Dict, settings: AppSettings):
        # Stop any prior background metadata fetchers safely
        self._cleanup_bg_metadata()  # NEW
        if self.downloader:
            try:
                self.downloader.stop()
            except Exception:
                pass
            self.downloader = None
        self.items = selection.get("items", [])
        self.kind = selection.get("kind", settings.defaults.kind)
        self.fmt = selection.get("format", settings.defaults.format)
        self.quality = selection.get("quality", "best")
        self._populate()

    def _populate(self):
        self.list.clear()
        for idx, it in enumerate(self.items):
            title = it.get("title") or "Untitled"
            w = DownloadItemWidget(title)
            # CHANGED: no background metadata here; assume items are ready
            w.status.setText("Waiting...")
            w.progress.setRange(0, 100)
            w.progress.setValue(0)
            thumb_url = it.get("thumbnail") or (it.get("thumbnails") or [{}])[-1].get(
                "url"
            )
            if thumb_url:
                try:
                    import requests

                    r = requests.get(thumb_url, timeout=6)
                    if r.ok:
                        pix = QPixmap()
                        if pix.loadFromData(r.content):
                            w.thumb.setPixmap(pix)
                except Exception:
                    pass
            item = QListWidgetItem()
            item.setSizeHint(w.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, w)
        self.btn_start.setEnabled(True)
        self.btn_start.setText("Start")
        self.btn_done.setVisible(False)
        self.btn_stop.setEnabled(False)

        # CHANGED: do not start background metadata fetching
        # if getattr(self.settings.ui, "background_metadata_enabled", True):
        #     self._start_bg_metadata()

    def _start_bg_metadata(self):
        for idx, it in enumerate(self.items):
            if not self._needs_metadata(it) or idx in self._meta_fetchers:
                continue
            url = it.get("webpage_url") or it.get("url")
            if not url:
                continue
            f = InfoFetcher(url)

            def _ok(meta: dict, i=idx):
                try:
                    self.items[i] = {**self.items[i], **(meta or {})}
                    w = self._get_widget(i)
                    if w:
                        title = self.items[i].get("title") or "Untitled"
                        w.title.setText(title)
                        turl = self.items[i].get("thumbnail") or (
                            self.items[i].get("thumbnails") or [{}]
                        )[-1].get("url")
                        if turl:
                            try:
                                import requests

                                r = requests.get(turl, timeout=6)
                                if r.ok:
                                    px = QPixmap()
                                    if px.loadFromData(r.content):
                                        w.thumb.setPixmap(px)
                            except Exception:
                                pass
                        w.status.setText("Waiting...")
                        w.progress.setRange(0, 100)
                        w.progress.setValue(0)
                finally:
                    self._meta_fetchers.pop(i, None)

            def _fail(err: str, i=idx):
                self._meta_fetchers.pop(i, None)

            f.finished_ok.connect(_ok)
            f.finished_fail.connect(_fail)
            self._meta_fetchers[idx] = f
            f.start()

    def _cleanup_bg_metadata(self):  # NEW
        # Disconnect finished signals to avoid updating stale widgets on later runs
        for i, f in list(self._meta_fetchers.items()):
            try:
                f.finished_ok.disconnect()
            except Exception:
                pass
            try:
                f.finished_fail.disconnect()
            except Exception:
                pass
        self._meta_fetchers.clear()

    # NEW: small helper to mirror Downloader heuristic
    def _needs_metadata(self, it: dict) -> bool:
        if not it:
            return True
        if not it.get("url") and not it.get("webpage_url"):
            return False
        has_core = (
            bool(it.get("id")) or bool(it.get("duration")) or bool(it.get("extractor"))
        )
        has_thumb = bool(it.get("thumbnail")) or bool(it.get("thumbnails"))
        return not (has_core and has_thumb)

    def _toggle_start_pause(self):
        if not self.downloader:
            self.start_downloads()
            return
        # Toggle pause/resume
        if self.downloader.is_paused():
            self.downloader.resume()
            self.btn_start.setText("Pause")
        else:
            self.downloader.pause()
            self.btn_start.setText("Resume")

    def start_downloads(self):
        if not self.items:
            return
        base = self.lbl_dir.text()
        os.makedirs(base, exist_ok=True)
        # Save last dir
        self.settings.last_download_dir = base
        self.settings_mgr.save(self.settings)

        # Ensure all items have a progress bar reset
        for i in range(self.list.count()):
            w = self._get_widget(i)
            if w:
                w.progress.setRange(0, 100)
                w.progress.setValue(0)

        ff_path = FF_DIR if os.path.exists(FF_EXE) else None
        self.downloader = Downloader(
            self.items, base, self.kind, self.fmt, ff_path, quality=self.quality
        )
        self.downloader.itemStatus.connect(self._on_item_status)
        self.downloader.itemProgress.connect(self._on_item_progress)
        self.downloader.itemThumb.connect(self._on_item_thumb)
        self.downloader.finished_all.connect(self._on_all_finished)
        self.btn_start.setText("Pause")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.downloader.start()

    def _stop_downloads(self):
        if self.downloader:
            try:
                self.downloader.stop()
            except Exception:
                pass
            self.downloader = None
        self.btn_start.setText("Start")
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        # CHANGED: just clear any old bg metadata threads if present
        self._cleanup_bg_metadata()

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(
            self, "Choose download folder", self.lbl_dir.text()
        )
        if d:
            self.lbl_dir.setText(d)

    def _on_item_status(self, idx: int, text: str):
        w = self._get_widget(idx)
        if w:
            w.status.setText(text)
            # Busy indicator for processing phase
            if text.startswith("Processing"):
                w.progress.setRange(0, 0)  # indeterminate
            elif (
                text.startswith("Error")
                or text.startswith("Done")
                or text.startswith("Stopped")
            ):
                w.progress.setRange(0, 100)

    def _on_item_progress(
        self, idx: int, percent: float, speed: float, eta: Optional[int]
    ):
        w = self._get_widget(idx)
        if w:
            # Ensure determinate during downloading
            if w.progress.minimum() == 0 and w.progress.maximum() == 0:
                w.progress.setRange(0, 100)
            w.progress.setValue(int(percent))
            if eta is not None:
                w.status.setText(
                    f"{percent:.1f}% | {speed/1024/1024:.2f} MB/s | ETA {eta}s"
                )

    def _on_item_thumb(self, idx: int, data: bytes):
        w = self._get_widget(idx)
        if w:
            pix = QPixmap()
            if pix.loadFromData(data):
                w.thumb.setPixmap(pix)

    def _get_widget(self, idx: int) -> Optional[DownloadItemWidget]:
        it = self.list.item(idx)
        if not it:
            return None
        return self.list.itemWidget(it)

    def _on_all_finished(self):
        self.btn_done.setVisible(True)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_start.setText("Start")
        self.downloader = None
        if self.settings.ui.reset_after_downloads:
            self.btn_done.setText("Reset")
        else:
            self.btn_done.setText("Done")
        self.allFinished.emit()

    def _done_clicked(self):
        # Parent will decide behavior, here we just reset the list UI
        self.reset()

    def reset(self):
        self._cleanup_bg_metadata()
        self.list.clear()
        self.items = []
        self.downloader = None
        self.btn_start.setText("Start")
        self.btn_start.setEnabled(False)
        self.btn_done.setVisible(False)
        self.downloader = None
        self.btn_start.setText("Start")  # NEW: ensure label is correct after reset
        self.btn_start.setEnabled(False)
        self.btn_done.setVisible(False)
