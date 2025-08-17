import re
from typing import Dict, List
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
from PyQt6.QtGui import QIcon, QPixmap, QColor
from urllib.parse import urlparse, parse_qs

from core.settings import AppSettings
from core.yt_manager import InfoFetcher

YOUTUBE_URL_RE = re.compile(r"https?://[^\s]+")
VIDEO_HOSTS = ("www.youtube.com", "m.youtube.com", "youtube.com", "youtu.be")


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

        # Debounce timer for search-as-you-type
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self._do_debounced_search)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Top row: input + multi toggle + Paste
        top = QHBoxLayout()
        self.txt = QLineEdit()
        self.txt.setPlaceholderText(
            "Paste a YouTube URL or type to search, then press Enter…"
        )
        self.chk_multi = QCheckBox("Add multiple")
        self.chk_multi.setObjectName("ButtonLike")  # styled as a button
        self.chk_multi.setChecked(False)
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
        self.playlist_list = QListWidget()
        self.playlist_list.setIconSize(QSize(96, 54))
        pl_lay.addWidget(self.playlist_list, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.btn_next = QPushButton("Next")
        bottom.addWidget(self.btn_next)
        lay.addLayout(bottom)

        # Signals
        self.btn_paste.clicked.connect(self._paste)
        self.txt.returnPressed.connect(self._enter_pressed)
        self.txt.textChanged.connect(self._on_text_changed)
        self.results.itemClicked.connect(self._toggle_from_results)
        self.selected_list.itemClicked.connect(self._remove_from_selected_prompt)
        self.playlist_list.itemClicked.connect(self._toggle_from_playlist)
        self.btn_next.clicked.connect(self._confirm_selection)

    # --- typing and debounce handling ---
    def _on_text_changed(self, _text: str):
        q = self.txt.text().strip()
        if not q:
            self.search_timer.stop()
            return
        # Cancel any in-flight fetch when user continues typing
        if self.fetcher and self.fetcher.isRunning():
            try:
                self.fetcher.terminate()
                self.fetcher.wait(500)
            except Exception:
                pass
            finally:
                self.fetcher = None
        # URLs: honor auto-fetch URLs immediately
        if YOUTUBE_URL_RE.match(q):
            if self.settings.ui.auto_fetch_urls:
                self._start_fetch(q)
            return
        # Text search: only when auto_search_text is enabled
        if not self.settings.ui.auto_search_text:
            return
        # If live_search enabled, schedule a debounce; otherwise wait for Enter
        if getattr(self.settings.ui, "live_search", False):
            secs = max(0, int(getattr(self.settings.ui, "search_debounce_seconds", 3)))
            self.search_timer.start(secs * 1000)
        else:
            self.search_timer.stop()

    def _do_debounced_search(self):
        q = self.txt.text().strip()
        if not q or YOUTUBE_URL_RE.match(q):
            return
        self._start_fetch(f"ytsearch20:{q}")

    def _paste(self):
        from PyQt6.QtWidgets import QApplication

        txt = QApplication.clipboard().text().strip()
        if not txt:
            return
        self.txt.setText(txt)
        self._maybe_auto_fetch()

    def _enter_pressed(self):
        q = self.txt.text().strip()
        if not q:
            return
        if YOUTUBE_URL_RE.match(q):
            # Try fast-path first
            if self._try_fast_single_url(q):
                return
            self._start_fetch(q)
        else:
            self._start_fetch(f"ytsearch20:{q}")

    def _maybe_auto_fetch(self):
        q = self.txt.text().strip()
        if not q:
            return
        if YOUTUBE_URL_RE.match(q):
            if self.settings.ui.auto_fetch_urls:
                if self._try_fast_single_url(q):
                    return
                self._start_fetch(q)
        else:
            if self.settings.ui.auto_search_text:
                self._start_fetch(f"ytsearch20:{q}")

    def _is_simple_video_url(self, url: str) -> bool:
        try:
            u = urlparse(url)
            if u.netloc not in VIDEO_HOSTS:
                return False
            if u.netloc == "youtu.be":
                # youtu.be/<id>
                return bool(u.path.strip("/"))
            # youtube.com/watch?v=<id> without playlist list=
            if u.path == "/watch":
                q = parse_qs(u.query or "")
                return "v" in q and "list" not in q
            # shorts/<id>
            if u.path.startswith("/shorts/"):
                return True
        except Exception:
            pass
        return False

    def _try_fast_single_url(self, url: str) -> bool:
        # If clearly a single-video URL (not a playlist), skip yt-dlp info fetch
        if not self._is_simple_video_url(url):
            return False
        title = self.txt.text().strip() or url
        info = {"webpage_url": url, "url": url, "title": title}
        if (not self.chk_multi.isChecked()) and self.settings.ui.auto_advance:
            self.urlDetected.emit(info)
            self.requestAdvance.emit({"url": url, "info": info, "is_playlist": False})
        else:
            self._add_selected(info)
        # Optional: clear input if configured
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
        self.fetcher.finished_fail.connect(self._info_fail)
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
                self._style_playlist_item(it, self._is_selected(e))
                self.playlist_list.addItem(it)
            self.tabs.setTabVisible(self.idx_playlist, True)
            self.tabs.setCurrentIndex(self.idx_playlist)
            return

        # Single URL info
        if (not self.chk_multi.isChecked()) and self.settings.ui.auto_advance:
            self.urlDetected.emit(info)
            self.requestAdvance.emit(
                {"url": self.txt.text().strip(), "info": info, "is_playlist": False}
            )
        else:
            self._add_selected(info)

    def _info_fail(self, err: str):
        # Show error and allow another attempt
        self.lbl_status.setText(f"Error: {err}")

    def _style_playlist_item(self, item: QListWidgetItem, selected: bool):
        if selected:
            item.setForeground(QColor(self.settings.ui.accent_color_hex))
        else:
            item.setForeground(QColor("#8a8b90"))

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
        # New: do not block on yt-dlp fetch; add/advance immediately
        info = {
            "webpage_url": url,
            "url": url,
            "title": title,
            "thumbnail": data.get("thumbnail"),
            "thumbnails": data.get("thumbnails"),
        }
        if (not self.chk_multi.isChecked()) and self.settings.ui.auto_advance:
            self.urlDetected.emit(info)
            self.requestAdvance.emit({"url": url, "info": info, "is_playlist": False})
        else:
            self._add_selected(info)

    def _style_playlist_item(self, item: QListWidgetItem, selected: bool):
        if selected:
            item.setForeground(QColor(self.settings.ui.accent_color_hex))
        else:
            item.setForeground(QColor("#8a8b90"))

    def _toggle_from_results(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole) or {}
        url = data.get("webpage_url") or data.get("url")
        title = data.get("title") or "Unknown title"
        if not url:
            return
        # if in selected -> prompt to remove
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
        # New: do not block on yt-dlp fetch; add/advance immediately
        info = {
            "webpage_url": url,
            "url": url,
            "title": title,
            "thumbnail": data.get("thumbnail"),
            "thumbnails": data.get("thumbnails"),
        }
        if (not self.chk_multi.isChecked()) and self.settings.ui.auto_advance:
            self.urlDetected.emit(info)
            self.requestAdvance.emit({"url": url, "info": info, "is_playlist": False})
        else:
            self._add_selected(info)

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

    def _is_selected(self, info: Dict) -> bool:
        u = info.get("webpage_url") or info.get("url")
        return any(
            (it.get("webpage_url") or it.get("url")) == u for it in self.selected
        )

    def _add_selected(self, info: Dict):
        # Normalize
        if info.get("_type") == "playlist" and info.get("entries"):
            for e in info["entries"]:
                if e:
                    self.selected.append(e)
        else:
            self.selected.append(info)
        # After updating, toggle Selected tab visibility
        self._refresh_selected_list()
        has_selected = self.selected_list.count() > 0
        self.tabs.setTabVisible(self.idx_selected, has_selected)
        if has_selected:
            self.tabs.setCurrentIndex(self.idx_selected)

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
        # Update Selected tab visibility
        self.tabs.setTabVisible(self.idx_selected, self.selected_list.count() > 0)

    def _remove_from_selected_prompt(self, item: QListWidgetItem):
        info = item.data(Qt.ItemDataRole.UserRole) or {}
        title = info.get("title") or "Untitled"
        if (
            QMessageBox.question(
                self, "Remove video", f"Remove '{title}' from selected?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            url = info.get("webpage_url") or info.get("url")
            self.selected = [
                it
                for it in self.selected
                if (it.get("webpage_url") or it.get("url")) != url
            ]
            self._refresh_selected_list()

    def _confirm_selection(self):
        # Cancel any in-flight fetch before advancing
        if self.fetcher and self.fetcher.isRunning():
            try:
                self.fetcher.terminate()
                self.fetcher.wait(1000)
            except Exception:
                pass
            finally:
                self.fetcher = None
                self.lbl_status.setText("Cancelled.")
        if not self.selected:
            return
        self.selectionConfirmed.emit(self.selected[:])

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
        self.lbl_status.setText("")
        self.results.clear()
        self.selected.clear()
        self.selected_list.clear()
        self.tabs.setCurrentWidget(self.tab_search)
