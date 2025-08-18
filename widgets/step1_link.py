import re
from typing import Dict, List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
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
)
from PyQt6.QtGui import QIcon, QPixmap, QColor, QImage
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

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

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.fetcher = None
        self.selected: List[Dict] = []
        self._bg_fetchers = {}  # NEW: url -> InfoFetcher for background metadata

        # Debounce timer for search-as-you-type
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_debounced_search)

        # Suppress auto-fetch shortly after handling fast paste
        self._suppress_auto = False
        self._suppress_timer = QTimer(self)
        self._suppress_timer.setSingleShot(True)
        self._suppress_timer.timeout.connect(
            lambda: setattr(self, "_suppress_auto", False)
        )

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
        top.addWidget(self.chk_multi)  # moved before Paste
        top.addWidget(self.btn_paste)
        lay.addLayout(top)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(self.lbl_status)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_search = QWidget()
        self.tab_selected = QWidget()
        self.tab_playlist = QWidget()  # new tab for playlist selection
        self.tabs.addTab(self.tab_search, "Searched Videos")
        self.tabs.addTab(self.tab_selected, "Selected Videos")
        self.tabs.addTab(self.tab_playlist, "Playlist Videos")
        lay.addWidget(self.tabs, 1)
        self.idx_search, self.idx_selected, self.idx_playlist = 0, 1, 2
        # Hide initially
        self.tabs.setTabVisible(self.idx_selected, False)
        self.tabs.setTabVisible(self.idx_playlist, False)

        # Search tab content
        ts_lay = QVBoxLayout(self.tab_search)
        ts_lay.setContentsMargins(0, 0, 0, 0)
        self.results = QListWidget()
        self.results.setIconSize(QSize(96, 54))
        ts_lay.addWidget(self.results, 1)

        # Selected tab content
        sel_lay = QVBoxLayout(self.tab_selected)
        sel_lay.setContentsMargins(0, 0, 0, 0)
        self.selected_list = QListWidget()
        self.selected_list.setIconSize(QSize(96, 54))
        sel_lay.addWidget(self.selected_list, 1)

        # Playlist tab content
        pl_lay = QVBoxLayout(self.tab_playlist)
        pl_lay.setContentsMargins(0, 0, 0, 0)
        # NEW: Select all checkbox row
        self.chk_pl_select_all = QCheckBox("Select all")
        self.chk_pl_select_all.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.chk_pl_select_all.toggled.connect(self._on_pl_select_all_toggled)
        pl_lay.addWidget(self.chk_pl_select_all, 0, Qt.AlignmentFlag.AlignLeft)

        self.playlist_list = QListWidget()
        self.playlist_list.setIconSize(QSize(96, 54))
        pl_lay.addWidget(self.playlist_list, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_next = QPushButton("Next")
        self.btn_next.setVisible(False)  # show only when multi is enabled
        bottom.addWidget(self.btn_next)
        lay.addLayout(bottom)

        # Signals
        self.btn_paste.clicked.connect(self._paste)
        self.txt.returnPressed.connect(self._enter_pressed)
        self.txt.textChanged.connect(self._on_text_changed)
        self.chk_multi.toggled.connect(self._on_multi_toggled)
        self.results.itemClicked.connect(self._toggle_from_results)
        self.selected_list.itemClicked.connect(self._remove_from_selected_prompt)
        self.playlist_list.itemClicked.connect(self._toggle_from_playlist)
        self.btn_next.clicked.connect(self._confirm_selection)

    # Event filter to detect Ctrl+V and use our paste handler
    def eventFilter(self, obj, event):
        if obj is self.txt:
            try:
                from PyQt6.QtCore import QEvent
                from PyQt6.QtGui import QKeySequence
            except Exception:
                return super().eventFilter(obj, event)
            if event.type() == QEvent.Type.KeyPress:
                # Ctrl+V or Shift+Insert
                if event.matches(QKeySequence.StandardKey.Paste):
                    self._handle_paste_from_clipboard()
                    return True
        return super().eventFilter(obj, event)

    # Utils
    def _cancel_fetch(self):
        if self.fetcher and self.fetcher.isRunning():
            try:
                self.fetcher.terminate()
                self.fetcher.wait(500)
            except Exception:
                pass
            finally:
                self.fetcher = None

    def _paste(self):
        # Use the same handler for the Paste button
        self._handle_paste_from_clipboard()

    def _handle_paste_from_clipboard(self):
        from PyQt6.QtWidgets import QApplication

        txt = QApplication.clipboard().text().strip()
        if not txt:
            return
        # Reflect in UI
        self.txt.setText(txt)
        # Cancel any in-flight fetch and start fresh
        self._cancel_fetch()
        # Unified processing
        self._process_text(txt, trigger="paste")  # NEW

    # --- typing and debounce handling ---
    def _on_text_changed(self, _text: str):
        q = self.txt.text().strip()
        if not q:
            self.search_timer.stop()
            return
        # Cancel in-flight fetch when typing resumes
        self._cancel_fetch()
        # Unified processing with debounce handling embedded
        self._process_text(q, trigger="typing")  # NEW

    def _do_debounced_search(self):
        q = self.txt.text().strip()
        if not q or YOUTUBE_URL_RE.match(q):
            return
        self._start_fetch(f"ytsearch20:{q}")

    def _enter_pressed(self):
        q = self.txt.text().strip()
        if not q:
            return
        self._process_text(q, trigger="enter")  # NEW

    def _maybe_auto_fetch(self):
        # Route to unified handler to keep behavior consistent
        q = self.txt.text().strip()
        if not q:
            return
        self._process_text(q, trigger="auto")  # NEW

    # NEW: single entry point for handling text/URL inputs from any source
    def _process_text(self, text: str, trigger: str = "typing"):
        is_url = bool(YOUTUBE_URL_RE.match(text))
        if is_url:
            kind, norm = self._classify_url(text)
            self._handle_url(kind, norm)
            return
        # Text search: honor debounce prefs
        if not self.settings.ui.auto_search_text:
            return
        if getattr(self.settings.ui, "live_search", False):
            secs = max(0, int(getattr(self.settings.ui, "search_debounce_seconds", 3)))
            self.search_timer.start(secs * 1000)
        else:
            # Immediate search for non-live mode on enter/paste
            if trigger in ("enter", "paste"):
                self._start_fetch(f"ytsearch20:{text}")
            else:
                self.search_timer.stop()

    # NEW: centralized URL flow handling (single/playlist/radio)
    def _handle_url(self, kind: str, norm: str):
        if kind == "radio":
            self.lbl_status.setText("Radio playlists are not supported.")
            return
        if kind == "playlist":
            if not self.chk_multi.isChecked():
                self.chk_multi.setChecked(True)
            self._start_fetch(norm)
            return
        # single video
        if getattr(self.settings.ui, "fast_paste_enabled", True):
            if self._try_fast_single_url(norm):
                return
        self._start_fetch(norm)

    # --- core logic (unchanged) ---
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

    def _is_simple_video_url(self, url: str) -> bool:
        try:
            u = urlparse(url)
            if u.netloc not in VIDEO_HOSTS:
                return False
            if u.netloc == "youtu.be":
                return bool(u.path.strip("/"))
            if u.path == "/watch":
                q = parse_qs(u.query or "")
                return "v" in q and len(q.get("v", [])) > 0 and ("list" not in q)
            if u.path.startswith("/shorts/"):
                return True
        except Exception:
            pass
        return False

    def _try_fast_single_url(self, url: str) -> bool:
        if not self._is_simple_video_url(url):
            return False
        title = self.txt.text().strip() or url
        info = {"webpage_url": url, "url": url, "title": title}
        if not self.chk_multi.isChecked():
            # Always auto-advance when not in multi mode
            self.urlDetected.emit(info)
            self.requestAdvance.emit({"url": url, "info": info, "is_playlist": False})
        else:
            self._upsert_selected(info)
        if self.settings.ui.clear_input_after_fetch:
            self.txt.clear()
        self.lbl_status.setText("")
        return True

    def _start_fetch(self, url: str):
        if self.fetcher and self.fetcher.isRunning():
            return
        self.lbl_status.setText(
            "Searching..." if url.startswith("ytsearch") else "Fetching info..."
        )
        self.fetcher = InfoFetcher(url)
        self.fetcher.finished_ok.connect(self._info_ok)
        self.fetcher.finished_fail.connect(self._info_fail)  # keep hookup
        self.fetcher.start()

    def _info_ok(self, info: Dict):
        # Clear input if requested and it was a URL/playlist fetch
        if self.settings.ui.clear_input_after_fetch:
            self.txt.clear()
        self.lbl_status.setText("")
        # Search results
        if (
            info.get("_type") == "playlist"
            and info.get("extractor_key") == "YoutubeSearch"
        ):
            self.results.clear()
            for e in info.get("entries") or []:
                title = e.get("title") or "Unknown title"
                url = e.get("webpage_url") or e.get("url") or ""
                it = QListWidgetItem(title)
                it.setData(
                    Qt.ItemDataRole.UserRole,
                    {
                        "title": title,
                        "webpage_url": url,  # ensure consistent key
                        "url": url,
                        "thumbnail": e.get("thumbnail"),
                        "thumbnails": e.get("thumbnails"),
                    },
                )
                pix = self._load_thumb(
                    e.get("thumbnail") or (e.get("thumbnails") or [{}])[-1].get("url")
                )
                if pix:
                    it.setIcon(QIcon(pix))
                self.results.addItem(it)
            self.tabs.setCurrentIndex(self.idx_search)
            return

        # Real playlist (entries present)
        if info.get("_type") == "playlist" and info.get("entries"):
            self.lbl_status.setText(
                f"Loaded playlist with {len(info.get('entries') or [])} videos."
            )
            self.playlist_list.clear()
            # ensure "Select all" is unchecked initially
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
                    it.setData(ICON_PIXMAP_ROLE, pix)  # keep original pixmap
                self._style_playlist_item(it, self._is_selected(e))
                self.playlist_list.addItem(it)
            self.tabs.setTabVisible(self.idx_playlist, True)
            self.tabs.setCurrentIndex(self.idx_playlist)
            return

        # Single URL info
        if not self.chk_multi.isChecked():
            self.urlDetected.emit(info)
            self.requestAdvance.emit(
                {"url": self.txt.text().strip(), "info": info, "is_playlist": False}
            )
        else:
            self._upsert_selected(info)

    def _info_fail(self, err: str):
        self.lbl_status.setText(f"Error: {err}")
        try:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(self, "Fetch failed", str(err))
        except Exception:
            pass
        self.fetcher = None

    def _upsert_selected(self, info: Dict):
        url = (info or {}).get("webpage_url") or (info or {}).get("url")
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
        # NEW: background metadata fetch for this item if enabled
        if getattr(self.settings.ui, "background_metadata_enabled", True):
            self._ensure_bg_fetch_for(url)
        self._refresh_selected_list()
        has_selected = self.selected_list.count() > 0
        self.tabs.setTabVisible(self.idx_selected, has_selected)
        if has_selected:
            self.tabs.setCurrentIndex(self.idx_selected)

    # NEW: start a bg fetch if item lacks metadata/thumbnail
    def _needs_metadata(self, it: dict) -> bool:
        if not it:
            return True
        has_core = (
            bool(it.get("id")) or bool(it.get("duration")) or bool(it.get("extractor"))
        )
        has_thumb = bool(it.get("thumbnail")) or bool(it.get("thumbnails"))
        return not (has_core and has_thumb)

    def _ensure_bg_fetch_for(self, url: str):
        if not url or url in self._bg_fetchers:
            return
        # Find current info by url
        it = next(
            (x for x in self.selected if (x.get("webpage_url") or x.get("url")) == url),
            None,
        )
        if not it or not self._needs_metadata(it):
            return
        f = InfoFetcher(url)

        def _ok(meta: dict, u=url):
            try:
                # Merge back into selected and keep reference to merged info
                merged_info = None
                for i, x in enumerate(self.selected):
                    xu = x.get("webpage_url") or x.get("url")
                    if xu == u:
                        self.selected[i] = {**x, **(meta or {})}
                        merged_info = self.selected[i]
                        break
                # Refresh selected list (title + icon)
                self._refresh_selected_list()
                # Also update playlist list icon/title if present
                if merged_info:
                    for k in range(self.playlist_list.count()):
                        pl_item = self.playlist_list.item(k)
                        data = pl_item.data(Qt.ItemDataRole.UserRole) or {}
                        du = data.get("webpage_url") or data.get("url")
                        if du == u:
                            pl_item.setText(merged_info.get("title") or "Untitled")
                            pix = self._load_thumb(
                                merged_info.get("thumbnail")
                                or (merged_info.get("thumbnails") or [{}])[-1].get(
                                    "url"
                                )
                            )
                            if pix:
                                pl_item.setIcon(QIcon(pix))
                                pl_item.setData(ICON_PIXMAP_ROLE, pix)
                            break
            finally:
                self._bg_fetchers.pop(u, None)

        def _fail(err: str, u=url):
            self._bg_fetchers.pop(u, None)

        f.finished_ok.connect(_ok)
        f.finished_fail.connect(_fail)
        self._bg_fetchers[url] = f
        f.start()

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

    def _on_multi_toggled(self, checked: bool):
        # Show Next only when multi is enabled
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
                # Reset playlist item styling (no items selected anymore)
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    self._style_playlist_item(it, False)
                self.lbl_status.setText("")
            else:
                # Revert toggle back to ON
                self.chk_multi.blockSignals(True)
                self.chk_multi.setChecked(True)
                self.chk_multi.blockSignals(False)

    def _on_pl_select_all_toggled(self, checked: bool):
        # NEW: select/deselect all videos from the current playlist view
        self.playlist_list.setUpdatesEnabled(False)
        try:
            if checked:
                # Add all to selected
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    # upsert
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
                    # Kick background metadata if enabled
                    if getattr(self.settings.ui, "background_metadata_enabled", True):
                        self._ensure_bg_fetch_for(u)
            else:
                # Remove all from selected
                urls = []
                for i in range(self.playlist_list.count()):
                    it = self.playlist_list.item(i)
                    e = it.data(Qt.ItemDataRole.UserRole) or {}
                    u = e.get("webpage_url") or e.get("url")
                    if not u:
                        continue
                    urls.append(u)
                    self._style_playlist_item(it, False)
                self.selected = [
                    s
                    for s in self.selected
                    if (s.get("webpage_url") or s.get("url")) not in set(urls)
                ]
            # Refresh the Selected tab
            self._refresh_selected_list()
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)
        finally:
            self.playlist_list.setUpdatesEnabled(True)

    def _toggle_from_playlist(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        url = info.get("webpage_url") or info.get("url")
        if not url:
            return
        if self._is_selected(info):
            # remove
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
            # add
            self.selected.append(info)
            self._refresh_selected_list()
            self._style_playlist_item(item, True)

    def _toggle_from_results(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("webpage_url") or data.get("url")
        title = data.get("title") or "Unknown title"
        if not url:
            return
        # If already selected -> prompt to remove
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
        # Add or auto-advance
        info = {
            "webpage_url": url,
            "url": url,
            "title": title,
            "thumbnail": data.get("thumbnail"),
            "thumbnails": data.get("thumbnails"),
        }
        if not self.chk_multi.isChecked():
            self.urlDetected.emit(info)
            self.requestAdvance.emit({"url": url, "info": info, "is_playlist": False})
        else:
            # Upsert to selected and trigger bg metadata if enabled
            self._upsert_selected(info)
            if getattr(self.settings.ui, "background_metadata_enabled", True):
                self._ensure_bg_fetch_for(url)

    # Small helper: safely load a thumbnail QPixmap from URL (returns None on any error)
    def _load_thumb(self, url):
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

    # Utils: grayscale and icon styling (used by playlist list items)
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

    def reset(self):
        # Cancel any in-flight fetch
        self._cancel_fetch()
        # Clear inputs and status
        self.txt.clear()
        self.lbl_status.setText("")
        # Clear all lists
        self.results.clear()
        self.playlist_list.clear()
        self.selected.clear()
        self.selected_list.clear()
        # Hide tabs except search, uncheck "Select all" and "Add multiple"
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
        # Reset timers/flags
        self._suppress_auto = False
        self.search_timer.stop()

    # Handle clicks on the "Selected Videos" list: prompt and remove
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
            # Remove from selection
            self.selected = [
                it
                for it in self.selected
                if (it.get("webpage_url") or it.get("url")) != url
            ]
            self._refresh_selected_list()
            # Update playlist styling for this item, if present there
            for i in range(self.playlist_list.count()):
                pit = self.playlist_list.item(i)
                pdata = pit.data(Qt.ItemDataRole.UserRole) or {}
                pu = pdata.get("webpage_url") or pdata.get("url")
                if pu == url:
                    self._style_playlist_item(pit, False)
                    break
            # Hide tab if empty
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # "Next" in multi-select mode: emit all selected infos
    def _confirm_selection(self):
        if not self.selected:
            QMessageBox.information(self, "No videos", "No videos selected.")
            return
        self.selectionConfirmed.emit(list(self.selected))
        title = info.get("title") or "Untitled"
        if not url:
            return
        if (
            QMessageBox.question(
                self, "Remove video", f"Remove '{title}' from selected?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            # Remove from selection
            self.selected = [
                it
                for it in self.selected
                if (it.get("webpage_url") or it.get("url")) != url
            ]
            self._refresh_selected_list()
            # Update playlist styling for this item, if present there
            for i in range(self.playlist_list.count()):
                pit = self.playlist_list.item(i)
                pdata = pit.data(Qt.ItemDataRole.UserRole) or {}
                pu = pdata.get("webpage_url") or pdata.get("url")
                if pu == url:
                    self._style_playlist_item(pit, False)
                    break
            # Hide tab if empty
            self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    # "Next" in multi-select mode: emit all selected infos
    def _confirm_selection(self):
        if not self.selected:
            QMessageBox.information(self, "No videos", "No videos selected.")
            return
        self.selectionConfirmed.emit(list(self.selected))
