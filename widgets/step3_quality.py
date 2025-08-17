from typing import List, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QComboBox,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtGui import QIcon, QPixmap

from core.settings import AppSettings, SettingsManager


class Step3QualityWidget(QWidget):
    qualityConfirmed = pyqtSignal(
        dict
    )  # {"items":[...], "kind":..., "format":..., "quality": ...}
    backRequested = pyqtSignal()

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.items: List[Dict] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Header row (Back)
        hdr = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        hdr.addWidget(self.btn_back)
        hdr.addStretch(1)
        lay.addLayout(hdr)

        self.lbl = QLabel("Choose what to download:")
        self.lbl.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(self.lbl)

        # Small preview list with thumbnails/titles
        self.preview = QListWidget()
        self.preview.setIconSize(QSize(96, 54))
        self.preview.setMaximumHeight(150)
        lay.addWidget(self.preview)

        # Kind row
        row = QHBoxLayout()
        self.rad_audio = QRadioButton("Audio")
        self.rad_video = QRadioButton("Video")
        row.addWidget(self.rad_audio)
        row.addWidget(self.rad_video)
        row.addStretch(1)
        lay.addLayout(row)

        self.cmb_format = QComboBox()
        self.cmb_format.setEditable(False)  # non-typable
        lay.addWidget(self.cmb_format)

        qrow = QHBoxLayout()
        qrow.addWidget(QLabel("Quality:"))
        self.cmb_quality = QComboBox()
        qrow.addWidget(self.cmb_quality, 1)
        lay.addLayout(qrow)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_next = QPushButton("Next")
        btn_row.addWidget(self.btn_next)
        lay.addLayout(btn_row)

        # Defaults
        if self.settings.defaults.kind == "audio":
            self.rad_audio.setChecked(True)
        else:
            self.rad_video.setChecked(True)
        self.cmb_format.addItems(
            ["mp3", "m4a", "flac", "wav", "opus", "mp4", "mkv", "webm"]
        )
        self.cmb_format.setCurrentText(self.settings.defaults.format)

        # Signals
        self.btn_back.clicked.connect(self.backRequested.emit)
        self.btn_next.clicked.connect(self._confirm)
        self.rad_audio.toggled.connect(self._kind_changed)

        self._kind_changed(self.rad_audio.isChecked())

    def set_items(self, items: List[Dict]):
        self.items = items
        self.lbl.setText(
            f"Selected {len(items)} item(s). Choose output format and quality."
        )
        # Populate preview with thumbnails
        self.preview.clear()
        for it in items:
            title = it.get("title") or "Untitled"
            lw = QListWidgetItem(title)
            pix = self._load_thumb(it)
            if pix:
                lw.setIcon(QIcon(pix))
            self.preview.addItem(lw)
        # Refresh quality options according to current kind
        self._populate_quality_options()

    def _load_thumb(self, it: Dict):
        url = it.get("thumbnail") or (it.get("thumbnails") or [{}])[-1].get("url")
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

    def _kind_changed(self, audio_checked: bool):
        # Update format suggestions
        if audio_checked:
            self.cmb_format.clear()
            self.cmb_format.addItems(["mp3", "m4a", "flac", "wav", "opus"])
        else:
            self.cmb_format.clear()
            self.cmb_format.addItems(["mp4", "mkv", "webm"])
        # Repopulate quality options for the selected kind
        self._populate_quality_options()

    def _populate_quality_options(self):
        self.cmb_quality.clear()
        # Default sets
        default_v = ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
        default_a = ["best", "320k", "256k", "192k", "160k", "128k"]
        first = self.items[0] if self.items else {}
        fmts = first.get("formats") or []
        if self.rad_audio.isChecked():
            # Collect available audio bitrates
            abrs = sorted(
                {
                    int(f.get("abr"))
                    for f in fmts
                    if f.get("abr") and f.get("acodec") != "none"
                },
                reverse=True,
            )
            opts = ["best"] + [f"{a}k" for a in abrs] if abrs else default_a
            self.cmb_quality.addItems(opts)
        else:
            heights = sorted(
                {
                    int(f.get("height"))
                    for f in fmts
                    if f.get("height") and f.get("vcodec") != "none"
                },
                reverse=True,
            )
            opts = ["best"] + [f"{h}p" for h in heights] if heights else default_v
            self.cmb_quality.addItems(opts)

    def _confirm(self):
        kind = "audio" if self.rad_audio.isChecked() else "video"
        fmt = self.cmb_format.currentText().strip()
        quality = self.cmb_quality.currentText().strip() or "best"
        # Remember last choice automatically
        self.settings.defaults.kind = kind
        self.settings.defaults.format = fmt
        SettingsManager().save(self.settings)
        self.qualityConfirmed.emit(
            {"items": self.items, "kind": kind, "format": fmt, "quality": quality}
        )
