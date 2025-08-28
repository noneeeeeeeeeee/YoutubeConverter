import re
from typing import Dict, List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QTabWidget,
    QMessageBox,
    QCheckBox,
    QProgressBar,
    QFrame,  # NEW
)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QImage
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from collections import deque

from core.settings import AppSettings
from core.yt_manager import InfoFetcher

YOUTUBE_URL_RE = re.compile(r"https?://[^\s]+")
VIDEO_HOSTS = ("www.youtube.com", "m.youtube.com", "youtube.com", "youtu.be")
ICON_PIXMAP_ROLE = int(Qt.ItemDataRole.UserRole) + 1  # store original pixmap


class Step1LinkWidget(QWidget):
    # Emits full info dict for a single immediate advance (when not multiple) for backward compat
    urlDetected = pyqtSignal(dict)
    requestAdvance = pyqtSignal(dict)
    # New: emit full list of selected info dicts
    selectionConfirmed = pyqtSignal(list)

    # Small worker to fetch a single thumbnail without blocking UI
    class _ThumbWorker(QThread):
        done = pyqtSignal(int, QPixmap, str)  # row, pixmap, url

        def __init__(self, row: int, url: str, parent=None):
            super().__init__(parent)
            self.row = row
            self.url = url

        def run(self):
            try:
                from urllib.request import urlopen

                data = urlopen(self.url, timeout=5).read()
                px = QPixmap()
                if px.loadFromData(data):
                    self.done.emit(self.row, px, self.url)
            except Exception:
                pass

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.fetcher = None
        self.selected: List[Dict] = []
        self._bg_fetchers = {}
        # Request management
        self._active_req_id = 0
        # self._pending_url: str | None = None  # REMOVED: replaced by queue
        self._thumb_threads: List[Step1LinkWidget._ThumbWorker] = []  # NEW
        # NEW: request queue and newest pending search coalescer
        self._queue = deque()  # type: deque[str]
        self._queued_search: str | None = None

        # NEW: confirm-fetch state
        self._confirm_inflight = False
        self._confirm_fetchers: dict[int, InfoFetcher] = {}
        self._confirm_total = 0
        self._confirm_done = 0

        # Setup UI
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Top row: input + multi toggle + Paste
        top = QHBoxLayout()
        self.txt = QLineEdit()
        self.txt.setPlaceholderText(
            "Paste a YouTube URL or type to search, then press Enter…"
        )
        # Intercept Ctrl+V to use the same fast-paste logic
        self.txt.installEventFilter(self)
        self.chk_multi = QCheckBox("Add multiple")
        self.chk_multi.setObjectName("ButtonLike")  # styled as a button
        self.chk_multi.setChecked(False)
        # prevent dotted focus on key navigation
        self.chk_multi.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_paste = QPushButton("Paste")
        top.addWidget(self.txt, 1)
        top.addWidget(self.chk_multi)
        top.addWidget(self.btn_paste)
        lay.addLayout(top)

        # NEW: Thin YouTube-like loading bar below the top row
        self.loading_bar = QProgressBar()
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setFixedHeight(3)
        self.loading_bar.setRange(0, 0)  # indeterminate
        self.loading_bar.setVisible(False)
        self.loading_bar.setStyleSheet(
            f"QProgressBar{{border:0;background:transparent;}}"
            f"QProgressBar::chunk{{background-color:{self.settings.ui.accent_color_hex};}}"
        )
        lay.addWidget(self.loading_bar)

        # Status row (keep only the label; remove spinner)
        status_row = QHBoxLayout()
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        status_row.addWidget(self.lbl_status, 1)
        lay.addLayout(status_row)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_search = QWidget()
        self.tab_selected = QWidget()
        self.tab_playlist = QWidget()
        self.tabs.addTab(self.tab_search, "Searched Videos")
        self.tabs.addTab(self.tab_selected, "Selected Videos")
        self.tabs.addTab(self.tab_playlist, "Playlist Videos")

        lay.addWidget(self.tabs, 1)
        self.idx_search, self.idx_selected, self.idx_playlist = 0, 1, 2
        self.tabs.setTabVisible(self.idx_selected, False)
        self.tabs.setTabVisible(self.idx_playlist, False)

        ts_lay = QVBoxLayout(self.tab_search)
        ts_lay.setContentsMargins(0, 0, 0, 0)
        self.results = QListWidget()
        self.results.setIconSize(QSize(96, 54))
        self.results.setFrameShape(QFrame.Shape.NoFrame)
        self.results.setSpacing(3)
        self.results.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        ts_lay.addWidget(self.results, 1)

        # Selected tab content
        sel_lay = QVBoxLayout(self.tab_selected)
        sel_lay.setContentsMargins(0, 0, 0, 0)
        self.selected_list = QListWidget()
        self.selected_list.setIconSize(QSize(96, 54))
        self.selected_list.setFrameShape(QFrame.Shape.NoFrame)
        self.selected_list.setSpacing(3)
        self.selected_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        sel_lay.addWidget(self.selected_list, 1)

        # Playlist tab content
        pl_lay = QVBoxLayout(self.tab_playlist)
        pl_lay.setContentsMargins(0, 0, 0, 0)
        self.chk_pl_select_all = QCheckBox("Select all")
        self.chk_pl_select_all.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chk_pl_select_all.toggled.connect(self._on_pl_select_all_toggled)
        pl_lay.addWidget(self.chk_pl_select_all, 0, Qt.AlignmentFlag.AlignLeft)

        self.playlist_list = QListWidget()
        self.playlist_list.setIconSize(QSize(96, 54))
        self.playlist_list.setFrameShape(QFrame.Shape.NoFrame)
        self.playlist_list.setSpacing(3)
        self.playlist_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        pl_lay.addWidget(self.playlist_list, 1)

        # Bottom row with Next button
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_next = QPushButton("Next")
        self.btn_next.setVisible(False)
        bottom.addWidget(self.btn_next)
        lay.addLayout(bottom)

        # Connect signals
        self.btn_paste.clicked.connect(self._paste)
        self.txt.returnPressed.connect(self._enter_pressed)
        self.txt.textChanged.connect(self._on_text_changed)
        self.chk_multi.toggled.connect(self._on_multi_toggled)
        self.results.itemClicked.connect(self._toggle_from_results)
        self.selected_list.itemClicked.connect(self._remove_from_selected_prompt)
        self.playlist_list.itemClicked.connect(self._toggle_from_playlist)
        self.btn_next.clicked.connect(self._confirm_selection)

        # Debounced search timer
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_debounced_search)

        # Ensure the Select-all toggle visibility matches multi-select state
        self.chk_pl_select_all.setVisible(self.chk_multi.isChecked())

    # ----- UI Helpers -----

    def _set_busy(self, on: bool):
        # Show/hide thin loading bar
        if on:
            self.loading_bar.setVisible(True)
            self.loading_bar.setRange(0, 0)
        else:
            self.loading_bar.setVisible(False)
            self.loading_bar.setRange(0, 1)
            self.loading_bar.setValue(0)

    def _refresh_selected_list(self):
        self.selected_list.clear()
        for it in self.selected:
            title = it.get("title") or "Untitled"
            lw = QListWidgetItem(title)
            thumb = (
                it.get("thumbnail") or (it.get("thumbnails") or [{}])[-1].get("url")
                if isinstance(it, dict)
                else None
            )
            pix = self._load_thumb(thumb)
            if pix:
                lw.setIcon(QIcon(pix))
            lw.setData(Qt.ItemDataRole.UserRole, it)
            self.selected_list.addItem(lw)
        self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # ----- Event Handlers -----

    def eventFilter(self, obj, event):
        if obj is self.txt:
            try:
                from PyQt6.QtCore import QEvent
                from PyQt6.QtGui import QKeySequence
            except Exception:
                return super().eventFilter(obj, event)
            if event.type() == QEvent.Type.KeyPress:
                if event.matches(QKeySequence.StandardKey.Paste):
                    self._handle_paste_from_clipboard()
                    return True
        return super().eventFilter(obj, event)

    def _paste(self):
        self._handle_paste_from_clipboard()

    def _handle_paste_from_clipboard(self):
        from PyQt6.QtWidgets import QApplication

        txt = (QApplication.clipboard().text() or "").strip()
        if not txt:
            return
        self.txt.setText(txt)
        self._process_text(txt, trigger="paste")

    def _on_text_changed(self, _: str):
        q = self.txt.text().strip()
        if not q:
            if hasattr(self, "search_timer"):
                self.search_timer.stop()
            self.lbl_status.setText("")
            self._set_busy(False)
            return
        self._process_text(q, trigger="typing")

    def _do_debounced_search(self):
        q = self.txt.text().strip()
        if not q or YOUTUBE_URL_RE.match(q):
            return
        self._start_fetch(f"ytsearch20:{q}")

    def _enter_pressed(self):
        q = self.txt.text().strip()
        if not q:
            return
        self._process_text(q, trigger="enter")

    # ----- URL Processing -----

    def _process_text(self, text: str, trigger: str = "typing"):
        text = (text or "").strip()
        if not text:
            return
        is_url = bool(YOUTUBE_URL_RE.match(text))
        if is_url:
            kind, norm = self._classify_url(text)
            self._handle_url(kind, norm)
            return

        auto = bool(getattr(self.settings.ui, "auto_search_text", True))  # CHANGED
        if not auto:
            if trigger in ("enter", "paste"):  # manual only
                self._start_fetch(f"ytsearch20:{text}")
            else:
                if hasattr(self, "search_timer"):
                    self.search_timer.stop()
            return

        # Auto search with debounce (single control)
        secs = max(0, int(getattr(self.settings.ui, "search_debounce_seconds", 3)))
        if not hasattr(self, "search_timer"):
            self.search_timer = QTimer(self)
            self.search_timer.setSingleShot(True)
            self.search_timer.timeout.connect(self._do_debounced_search)
        self.search_timer.start(secs * 1000)

    def _handle_url(self, kind: str, norm: str):
        if kind == "radio":
            self.lbl_status.setText("Radio playlists are not supported.")
            return
        if kind == "playlist":
            if not self.chk_multi.isChecked():
                self.chk_multi.setChecked(True)
            self._start_fetch(norm)
            return
        self._start_fetch(norm)

    def _classify_url(self, url: str) -> Tuple[str, str]:
        """
        Returns (kind, normalized_url)
        kind: 'single' | 'playlist' | 'radio' | 'unknown'
        """
        try:
            u = urlparse(url)
            if u.netloc not in VIDEO_HOSTS:
                return "unknown", url
            # youtu.be short form
            if u.netloc == "youtu.be":
                vid = u.path.strip("/")
                q = parse_qs(u.query or "")
                lst = (q.get("list") or [""])[0]
                if lst.startswith("RD") or q.get("start_radio", ["0"])[0] == "1":
                    return "radio", url
                if lst:
                    # normalize to watch with v+list
                    qs = urlencode({"v": vid, "list": lst}, doseq=True)
                    return "playlist", urlunparse(
                        ("https", "www.youtube.com", "/watch", "", qs, "")
                    )
                # single
                qs = urlencode({"v": vid}, doseq=True)
                return "single", urlunparse(
                    ("https", "www.youtube.com", "/watch", "", qs, "")
                )
            # shorts
            if u.path.startswith("/shorts/"):
                vid = u.path.split("/")[-1]
                qs = urlencode({"v": vid}, doseq=True)
                return "single", urlunparse(
                    (u.scheme or "https", "www.youtube.com", "/watch", "", qs, "")
                )
            # standard watch
            if u.path == "/watch":
                q = parse_qs(u.query or "")
                lst = (q.get("list") or [""])[0]
                if lst:
                    if lst.startswith("RD") or (q.get("start_radio", ["0"])[0] == "1"):
                        return "radio", url
                    # keep only v+list for playlist fetch
                    keep = {}
                    if "v" in q:
                        keep["v"] = q["v"]
                    keep["list"] = [lst]
                    qs = urlencode(keep, doseq=True)
                    return "playlist", urlunparse(
                        (u.scheme, u.netloc, u.path, u.params, qs, u.fragment)
                    )
                # single: keep v(+t)
                keep = {}
                if "v" in q:
                    keep["v"] = q["v"]
                if "t" in q:
                    keep["t"] = q["t"]
                qs = urlencode(keep, doseq=True)
                return "single", urlunparse(
                    (u.scheme, u.netloc, u.path, u.params, qs, u.fragment)
                )
        except Exception:
            return "unknown", url
        return "unknown", url

    # ----- Fetch and Queue Management -----

    def _start_fetch(self, url: str):
        if self.fetcher and self.fetcher.isRunning():
            # If a fetch is in progress, handle queuing
            if url.startswith("ytsearch"):
                self._queued_search = url  # Only keep latest search
                self.lbl_status.setText("Queued latest search...")
            else:
                self._queue.append(url)  # Queue non-search URLs in order
                self.lbl_status.setText("Queued request...")
            return

        self.lbl_status.setText(
            "Searching..." if url.startswith("ytsearch") else "Fetching info..."
        )
        self._set_busy(True)
        self.fetcher = InfoFetcher(url)
        req_id = self._active_req_id = self._active_req_id + 1

        self.fetcher.finished_ok.connect(
            lambda info, rid=req_id: self._on_fetch_ok(rid, info)
        )
        self.fetcher.finished_fail.connect(
            lambda err, rid=req_id: self._on_fetch_fail(rid, err)
        )
        self.fetcher.start()

    def _on_fetch_ok(self, rid: int, info: Dict):
        # Ignore stale responses
        if rid != self._active_req_id:
            return
        self.fetcher = None
        self._set_busy(False)

        # Clear input if requested
        if self.settings.ui.clear_input_after_fetch:
            self.txt.clear()
        self.lbl_status.setText("")

        # Handle search results
        if (
            info.get("_type") == "playlist"
            and info.get("extractor_key") == "YoutubeSearch"
        ):
            self.results.clear()
            entries = info.get("entries") or []
            for i, e in enumerate(entries):
                title = e.get("title") or "Unknown title"
                url = e.get("webpage_url") or e.get("url") or ""
                thumb = e.get("thumbnail") or (e.get("thumbnails") or [{}])[-1].get(
                    "url"
                )
                it = QListWidgetItem(title)
                it.setData(
                    Qt.ItemDataRole.UserRole,
                    {
                        "title": title,
                        "webpage_url": url,
                        "url": url,
                        "thumbnail": e.get("thumbnail"),
                        "thumbnails": e.get("thumbnails"),
                    },
                )
                # Defer thumbnail loading
                if thumb:
                    worker = Step1LinkWidget._ThumbWorker(i, thumb, self)
                    worker.done.connect(
                        lambda row, px, expected=thumb: self._set_result_icon_if_match(
                            row, px, expected
                        )
                    )
                    worker.finished.connect(
                        lambda w=worker: (
                            self._thumb_threads.remove(w)
                            if w in self._thumb_threads
                            else None
                        )
                    )
                    self._thumb_threads.append(worker)
                    worker.start()
                self.results.addItem(it)
            self.tabs.setCurrentIndex(self.idx_search)
            self._run_pending_if_any()
            return

        # Handle real playlist
        if info.get("_type") == "playlist" and info.get("entries"):
            self.lbl_status.setText(
                f"Loaded playlist with {len(info.get('entries') or [])} videos."
            )
            self.playlist_list.clear()
            self.chk_pl_select_all.blockSignals(True)
            self.chk_pl_select_all.setChecked(False)
            self.chk_pl_select_all.blockSignals(False)
            for e in info.get("entries") or []:
                if not e:
                    continue
                title = e.get("title") or "Untitled"
                it = QListWidgetItem(title)
                it.setData(Qt.ItemDataRole.UserRole, e)
                pix = self._load_thumb(
                    e.get("thumbnail") or (e.get("thumbnails") or [{}])[-1].get("url")
                )
                if pix:
                    it.setIcon(QIcon(pix))
                    it.setData(ICON_PIXMAP_ROLE, pix)
                self._style_playlist_item(it, self._is_selected(e))
                self.playlist_list.addItem(it)
            self.tabs.setTabVisible(self.idx_playlist, True)
            self.tabs.setCurrentIndex(self.idx_playlist)
            self.chk_pl_select_all.setVisible(self.chk_multi.isChecked())  # NEW
            self._run_pending_if_any()
            return

        # Handle single video
        if not self.chk_multi.isChecked():
            self.urlDetected.emit(info)
            self.requestAdvance.emit(
                {"url": self.txt.text().strip(), "info": info, "is_playlist": False}
            )
        else:
            self._upsert_selected(info)
        self._run_pending_if_any()

    def _on_fetch_fail(self, rid: int, err: str):
        # Ignore stale failures
        if rid != self._active_req_id:
            return
        self.fetcher = None
        self._set_busy(False)
        self.lbl_status.setText(f"Error: {err}")
        try:
            QMessageBox.warning(self, "Fetch failed", str(err))
        except Exception:
            pass
        self._run_pending_if_any()

    def _run_pending_if_any(self):
        # Process pending requests - newest search first, then FIFO queue
        next_url = None
        if self._queued_search:
            next_url = self._queued_search
            self._queued_search = None
        elif self._queue:
            next_url = self._queue.popleft()
        if next_url:
            self._start_fetch(next_url)

    def _cancel_fetch(self):
        # No-op: don't force-terminate fetches to avoid crashes
        pass

    # ----- Selection Management -----

    def _is_selected(self, info: Dict) -> bool:
        url = (info or {}).get("webpage_url") or (info or {}).get("url")
        if not url:
            return False
        return any(
            (it.get("webpage_url") or it.get("url")) == url for it in self.selected
        )

    def _upsert_selected(self, info: Dict):
        if not isinstance(info, dict):
            return
        url = info.get("webpage_url") or info.get("url")
        if not url:
            return
        idx = next(
            (
                i
                for i, it in enumerate(self.selected)
                if (it.get("webpage_url") or it.get("url")) == url
            ),
            -1,
        )
        if idx >= 0:
            self.selected[idx] = {**self.selected[idx], **info}
        else:
            self.selected.append(info)
        self._refresh_selected_list()

    # --- UI lock helper during confirm ---
    def _set_ui_enabled(self, enabled: bool):
        try:
            self.txt.setEnabled(enabled)
            self.btn_paste.setEnabled(enabled)
            self.chk_multi.setEnabled(enabled)
            self.tabs.setEnabled(enabled)
            self.results.setEnabled(enabled)
            self.selected_list.setEnabled(enabled)
            self.playlist_list.setEnabled(enabled)
            self.btn_next.setEnabled(enabled and self.chk_multi.isChecked())
        except Exception:
            pass

    # --- Confirm fetch all (parallel, URL-safe) ---
    def _fetch_all_selected_then_emit(self):
        # Collect URLs needing metadata (do not trust indices that can shift)
        def _has_formats(it: Dict) -> bool:
            fmts = it.get("formats")
            return bool(fmts and isinstance(fmts, list) and len(fmts) > 0)

        urls = []
        for it in list(self.selected):
            if not _has_formats(it):
                u = (it or {}).get("webpage_url") or (it or {}).get("url")
                if u:
                    urls.append(u)

        if not urls:
            self.selectionConfirmed.emit(list(self.selected))
            return
        if getattr(self, "_confirm_inflight", False):
            return

        self._confirm_inflight = True
        self._confirm_total = len(urls)
        self._confirm_done = 0
        self._confirm_fetchers = {}

        # Disable UI and show determinate progress
        self._set_ui_enabled(False)
        self.btn_next.setEnabled(False)
        self.loading_bar.setVisible(True)
        self.loading_bar.setRange(0, self._confirm_total)
        self.loading_bar.setValue(0)
        self.lbl_status.setText(
            f"Fetching metadata for {self._confirm_total} item(s)..."
        )

        def _on_done_one():
            self._confirm_done += 1
            try:
                self.loading_bar.setValue(self._confirm_done)
            except Exception:
                pass
            if self._confirm_done >= self._confirm_total:
                # Finalize
                self._confirm_inflight = False
                self._confirm_fetchers.clear()
                self.lbl_status.setText("")
                self.loading_bar.setVisible(False)
                self.loading_bar.setRange(0, 0)
                self._set_ui_enabled(True)
                self.btn_next.setEnabled(True)
                self.selectionConfirmed.emit(list(self.selected))

        # Launch parallel fetchers keyed by URL to avoid index drift
        for u in urls:
            f = InfoFetcher(u)

            def _ok(meta: dict, url=u):
                try:
                    if isinstance(meta, dict):
                        # merge into the matching selected item by URL if still present
                        for i, s in enumerate(list(self.selected)):
                            surl = (s or {}).get("webpage_url") or (s or {}).get("url")
                            if surl == url:
                                self.selected[i] = {**s, **meta}
                                break
                        self._refresh_selected_list()
                finally:
                    self._confirm_fetchers.pop(url, None)
                    _on_done_one()

            def _fail(_: str, url=u):
                self._confirm_fetchers.pop(url, None)
                _on_done_one()

            f.finished_ok.connect(_ok)
            f.finished_fail.connect(_fail)
            self._confirm_fetchers[u] = f
            f.start()

    # --- Multi toggle: also hide/show playlist "Select all" ---
    def _on_multi_toggled(self, checked: bool):
        self.btn_next.setVisible(checked)
        self.chk_pl_select_all.setVisible(checked)  # NEW
        if checked:
            return
        if self.selected:
            res = QMessageBox.question(
                self,
                "Clear selected",
                "Are you sure you want to clear videos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if res == QMessageBox.StandardButton.Yes:
                self.selected.clear()
                self._refresh_selected_list()
                self.tabs.setTabVisible(self.idx_selected, False)
                # Reset playlist item styling
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    self._style_playlist_item(it, False)
                self.lbl_status.setText("")
            else:
                # Revert to ON
                self.chk_multi.blockSignals(True)
                self.chk_multi.setChecked(True)
                self.chk_multi.blockSignals(False)
        # No selection to clear; still ensure status/UI consistent
        self.lbl_status.setText("")

    # Remove duplicate legacy handlers below to avoid conflicts
    # (If duplicates exist later in file, delete them or ensure only this set remains.)
    # ...existing code...

    # Toggle a playlist entry in/out of selection
    def _toggle_from_playlist(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        url = info.get("webpage_url") or info.get("url")
        if not url:
            return

        if self._is_selected(info):
            title = info.get("title") or "Untitled"
            if (
                QMessageBox.question(
                    self, "Remove video", f"Remove '{title}' from selected?"
                )
                == QMessageBox.StandardButton.Yes
            ):
                self.selected = [
                    it
                    for it in self.selected
                    if (it.get("webpage_url") or it.get("url")) != url
                ]
                self._refresh_selected_list()
                self._style_playlist_item(item, False)
        else:
            self.lbl_status.setText("Fetching info...")
            self._start_fetch(url)

    def reset(self):
        # Cancel any in-flight fetch
        self._cancel_fetch()
        # Clear inputs and status
        self.txt.clear()
        self.lbl_status.setText("")
        self._set_busy(False)  # CHANGED
        # Clear all lists
        self.results.clear()
        self.playlist_list.clear()
        self.selected.clear()
        self.selected_list.clear()
        # Hide tabs except search, uncheck toggles
        self.tabs.setCurrentWidget(self.tab_search)
        self.tabs.setTabVisible(self.idx_selected, False)
        self.tabs.setTabVisible(self.idx_playlist, False)
        self.chk_pl_select_all.blockSignals(True)
        self.chk_pl_select_all.setChecked(False)
        self.chk_pl_select_all.blockSignals(False)
        self.chk_multi.blockSignals(True)
        self.chk_multi.setChecked(False)
        self.chk_multi.blockSignals(False)
        self.btn_next.setVisible(False)
        # Stop any pending search timer cleanly
        if hasattr(self, "search_timer"):
            self.search_timer.stop()
        # Let thumb workers finish; icons will be ignored after list cleared
        self._thumb_threads.clear()

    # Keep only one definition of this handler
    def _remove_from_selected_prompt(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        url = info.get("webpage_url") or info.get("url")
        title = info.get("title") or "Untitled"
        if not url:
            return
        if (
            QMessageBox.question(
                self, "Remove video", f"Remove '{title}' from selected?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.selected = [
                it
                for it in self.selected
                if (it.get("webpage_url") or it.get("url")) != url
            ]
            self._refresh_selected_list()
            for i in range(self.playlist_list.count()):
                pit = self.playlist_list.item(i)
                pdata = pit.data(Qt.ItemDataRole.UserRole) or {}
                pu = pdata.get("webpage_url") or pdata.get("url")
                if pu == url:
                    self._style_playlist_item(pit, False)
                    break
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # "Next" in multi-select mode: emit all selected infos
    def _confirm_selection(self):
        if not self.selected:
            QMessageBox.information(self, "No videos", "No videos selected.")
            return
        self._fetch_all_selected_then_emit()

    # ----- Thumbnail and Styling Helpers (ADDED) -----
    def _load_thumb(self, url: str):
        if not url:
            return None
        try:
            from urllib.request import urlopen

            data = urlopen(url, timeout=5).read()
            pix = QPixmap()
            if pix.loadFromData(data):
                return pix
        except Exception:
            pass
        return None

    def _to_gray(self, pix: QPixmap) -> QPixmap:
        try:
            img = pix.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
            return QPixmap.fromImage(img)
        except Exception:
            return pix

    def _apply_icon_style(self, item: QListWidgetItem, selected: bool):
        pix = item.data(ICON_PIXMAP_ROLE)
        if isinstance(pix, QPixmap):
            item.setIcon(QIcon(pix if selected else self._to_gray(pix)))

    def _style_playlist_item(self, item: QListWidgetItem, selected: bool):
        if selected:
            item.setForeground(QColor(self.settings.ui.accent_color_hex))
        else:
            item.setForeground(QColor("#8a8b90"))
        self._apply_icon_style(item, selected)

    def _set_result_icon_if_match(self, row: int, pix: QPixmap, expected_url: str):
        try:
            if row < 0 or row >= self.results.count():
                return
            it = self.results.item(row)
            data = it.data(Qt.ItemDataRole.UserRole) or {}
            current = data.get("thumbnail") or (data.get("thumbnails") or [{}])[-1].get(
                "url"
            )
            if current != expected_url:
                return  # item changed; skip
            it.setIcon(QIcon(pix))
            it.setData(ICON_PIXMAP_ROLE, pix)
        except Exception:
            pass
        self._thumb_threads.clear()

    # Keep only one definition of this handler
    def _remove_from_selected_prompt(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        url = info.get("webpage_url") or info.get("url")
        title = info.get("title") or "Untitled"
        if not url:
            return
        if (
            QMessageBox.question(
                self, "Remove video", f"Remove '{title}' from selected?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.selected = [
                it
                for it in self.selected
                if (it.get("webpage_url") or it.get("url")) != url
            ]
            self._refresh_selected_list()
            for i in range(self.playlist_list.count()):
                pit = self.playlist_list.item(i)
                pdata = pit.data(Qt.ItemDataRole.UserRole) or {}
                pu = pdata.get("webpage_url") or pdata.get("url")
                if pu == url:
                    self._style_playlist_item(pit, False)
                    break
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # "Next" in multi-select mode: emit all selected infos
    def _confirm_selection(self):
        if not self.selected:
            QMessageBox.information(self, "No videos", "No videos selected.")
            return
        # Ensure all selected have metadata before emitting
        self._fetch_all_selected_then_emit()

    def _toggle_from_results(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("webpage_url") or data.get("url")
        title = data.get("title") or "Unknown title"
        if not url:
            return
        idx = next(
            (
                i
                for i, it in enumerate(self.selected)
                if (it.get("webpage_url") or it.get("url")) == url
            ),
            -1,
        )
        if idx >= 0:
            if (
                QMessageBox.question(
                    self, "Remove video", f"Remove '{title}' from selected?"
                )
                == QMessageBox.StandardButton.Yes
            ):
                self.selected.pop(idx)
                self._refresh_selected_list()
            return
        # Always fetch full metadata before proceeding (no background fetch)
        self.lbl_status.setText("Fetching info...")
        self._start_fetch(url)

    # NEW: handler for the "Select all" checkbox in the playlist tab
    def _on_pl_select_all_toggled(self, checked: bool):
        # Select/deselect all playlist entries, updating self.selected accordingly.
        self.playlist_list.setUpdatesEnabled(False)
        try:
            if checked:
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    idx = next(
                        (
                            k
                            for k, s in enumerate(self.selected)
                            if (s.get("webpage_url") or s.get("url")) == u
                        ),
                        -1,
                    )
                    if idx >= 0:
                        self.selected[idx] = {**self.selected[idx], **e}
                    else:
                        self.selected.append(e)
                    self._style_playlist_item(it, True)
            else:
                # Remove any selected item that belongs to this playlist view
                urls = []
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    urls.append(u)
                    self._style_playlist_item(it, False)
                urlset = set(urls)
                self.selected = [
                    s
                    for s in self.selected
                    if (s.get("webpage_url") or s.get("url")) not in urlset
                ]
            self._refresh_selected_list()
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)
        finally:
            self.playlist_list.setUpdatesEnabled(True)

    # NEW: handler for the "Select all" checkbox in the playlist tab
    def _on_pl_select_all_toggled(self, checked: bool):
        # Select/deselect all playlist entries, updating self.selected accordingly.
        self.playlist_list.setUpdatesEnabled(False)
        try:
            if checked:
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    idx = next(
                        (
                            k
                            for k, s in enumerate(self.selected)
                            if (s.get("webpage_url") or s.get("url")) == u
                        ),
                        -1,
                    )
                    if idx >= 0:
                        self.selected[idx] = {**self.selected[idx], **e}
                    else:
                        self.selected.append(e)
                    self._style_playlist_item(it, True)
            else:
                # Remove any selected item that belongs to this playlist view
                urls = []
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    urls.append(u)
                    self._style_playlist_item(it, False)
                urlset = set(urls)
                self.selected = [
                    s
                    for s in self.selected
                    if (s.get("webpage_url") or s.get("url")) not in urlset
                ]
            self._refresh_selected_list()
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)
        finally:
            self.playlist_list.setUpdatesEnabled(True)

    # Show Next only when multi is enabled; confirm clear when disabling
    def _on_multi_toggled(self, checked: bool):
        self.btn_next.setVisible(checked)
        if checked:
            return
        if self.selected:
            res = QMessageBox.question(
                self,
                "Clear selected",
                "Are you sure you want to clear videos?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if res == QMessageBox.StandardButton.Yes:
                self.selected.clear()
                self._refresh_selected_list()
                self.tabs.setTabVisible(self.idx_selected, False)
                # Reset playlist item styling
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    self._style_playlist_item(it, False)
                self.lbl_status.setText("")
            else:
                # Revert to ON
                self.chk_multi.blockSignals(True)
                self.chk_multi.setChecked(True)
                self.chk_multi.blockSignals(False)

    # Show Next only when multi is enabled; confirm clear when disabling
    # (already defined above, removed duplicate)

    def reset(self):
        # Cancel any in-flight fetch
        self._cancel_fetch()
        # Clear inputs and status
        self.txt.clear()
        self.lbl_status.setText("")
        self._set_busy(False)  # CHANGED
        # Clear all lists
        self.results.clear()
        self.playlist_list.clear()
        self.selected.clear()
        self.selected_list.clear()
        # Hide tabs except search, uncheck toggles
        self.tabs.setCurrentWidget(self.tab_search)
        self.tabs.setTabVisible(self.idx_selected, False)
        self.tabs.setTabVisible(self.idx_playlist, False)
        self.chk_pl_select_all.blockSignals(True)
        self.chk_pl_select_all.setChecked(False)
        self.chk_pl_select_all.blockSignals(False)
        self.chk_multi.blockSignals(True)
        self.chk_multi.setChecked(False)
        self.chk_multi.blockSignals(False)
        self.btn_next.setVisible(False)
        # Stop any pending search timer cleanly
        if hasattr(self, "search_timer"):
            self.search_timer.stop()
        # Let thumb workers finish; icons will be ignored after list cleared
        self._thumb_threads.clear()

    # Keep only one definition of this handler
    def _remove_from_selected_prompt(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        url = info.get("webpage_url") or info.get("url")
        title = info.get("title") or "Untitled"
        if not url:
            return
        if (
            QMessageBox.question(
                self, "Remove video", f"Remove '{title}' from selected?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.selected = [
                it
                for it in self.selected
                if (it.get("webpage_url") or it.get("url")) != url
            ]
            self._refresh_selected_list()
            for i in range(self.playlist_list.count()):
                pit = self.playlist_list.item(i)
                pdata = pit.data(Qt.ItemDataRole.UserRole) or {}
                pu = pdata.get("webpage_url") or pdata.get("url")
                if pu == url:
                    self._style_playlist_item(pit, False)
                    break
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # "Next" in multi-select mode: emit all selected infos
    def _confirm_selection(self):
        if not self.selected:
            QMessageBox.information(self, "No videos", "No videos selected.")
            return
        self._fetch_all_selected_then_emit()

    def _toggle_from_results(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("webpage_url") or data.get("url")
        title = data.get("title") or "Unknown title"
        if not url:
            return
        idx = next(
            (
                i
                for i, it in enumerate(self.selected)
                if (it.get("webpage_url") or it.get("url")) == url
            ),
            -1,
        )
        if idx >= 0:
            if (
                QMessageBox.question(
                    self, "Remove video", f"Remove '{title}' from selected?"
                )
                == QMessageBox.StandardButton.Yes
            ):
                self.selected.pop(idx)
                self._refresh_selected_list()
            return
        # Always fetch full metadata before proceeding (no background fetch)
        self.lbl_status.setText("Fetching info...")
        self._start_fetch(url)

    # NEW: handler for the "Select all" checkbox in the playlist tab
    def _on_pl_select_all_toggled(self, checked: bool):
        # Select/deselect all playlist entries, updating self.selected accordingly.
        self.playlist_list.setUpdatesEnabled(False)
        try:
            if checked:
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    idx = next(
                        (
                            k
                            for k, s in enumerate(self.selected)
                            if (s.get("webpage_url") or s.get("url")) == u
                        ),
                        -1,
                    )
                    if idx >= 0:
                        self.selected[idx] = {**self.selected[idx], **e}
                    else:
                        self.selected.append(e)
                    self._style_playlist_item(it, True)
            else:
                # Remove any selected item that belongs to this playlist view
                urls = []
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    urls.append(u)
                    self._style_playlist_item(it, False)
                urlset = set(urls)
                self.selected = [
                    s
                    for s in self.selected
                    if (s.get("webpage_url") or s.get("url")) not in urlset
                ]
            self._refresh_selected_list()
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)
        finally:
            self.playlist_list.setUpdatesEnabled(True)
            self._thumb_threads.clear()

    # "Next" in multi-select mode: emit all selected infos
    def _confirm_selection(self):
        if not self.selected:
            QMessageBox.information(self, "No videos", "No videos selected.")
            return
        # Ensure all selected have metadata before emitting
        self._fetch_all_selected_then_emit()

    def _toggle_from_results(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("webpage_url") or data.get("url")
        title = data.get("title") or "Unknown title"
        if not url:
            return
        idx = next(
            (
                i
                for i, it in enumerate(self.selected)
                if (it.get("webpage_url") or it.get("url")) == url
            ),
            -1,
        )
        if idx >= 0:
            if (
                QMessageBox.question(
                    self, "Remove video", f"Remove '{title}' from selected?"
                )
                == QMessageBox.StandardButton.Yes
            ):
                self.selected.pop(idx)
                self._refresh_selected_list()
            return
        # Always fetch full metadata before proceeding (no background fetch)
        self.lbl_status.setText("Fetching info...")
        self._start_fetch(url)
