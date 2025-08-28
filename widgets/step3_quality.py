from typing import List, Dict
from PyQt6.QtCore import (
    Qt,
    pyqtSignal,
    QSize,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QAbstractAnimation,
    QEvent,
    QObject,
)
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,  # CHANGED: moved here from QtGui
)
from PyQt6.QtGui import QIcon, QPixmap  # CHANGED: removed QGraphicsOpacityEffect

from core.settings import AppSettings, SettingsManager
from core.yt_manager import InfoFetcher


class Step3QualityWidget(QWidget):
    qualityConfirmed = pyqtSignal(
        dict
    )  # {"items":[...], "kind":..., "format":..., "quality": ...}
    backRequested = pyqtSignal()

    def __init__(self, settings: AppSettings):
        super().__init__()
        self.settings = settings
        self.items: List[Dict] = []
        self._meta_fetchers: List[InfoFetcher] = []  # running re-fetchers
        self._url_index: Dict[str, int] = {}  # map url->index for quick updates

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Header
        self.header = QLabel("Choose what to download")
        self.header.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        font = self.header.font()
        font.setPointSize(font.pointSize() + 1)
        font.setBold(True)
        self.header.setFont(font)
        root.addWidget(self.header)

        # Content: preview (left) + options (right)
        content = QHBoxLayout()
        content.setSpacing(10)
        root.addLayout(content, 1)

        # Left: preview
        self.preview = QListWidget()
        self.preview.setIconSize(QSize(96, 54))
        self.preview.setAlternatingRowColors(False)
        self.preview.setFrameShape(QFrame.Shape.NoFrame)
        self.preview.setSpacing(4)  # CHANGED: tighter spacing
        self.preview.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        content.addWidget(self.preview, 2)

        # NEW: accent vertical separator between list and options
        vsep = QFrame()
        vsep.setObjectName("AccentVLine")
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setLineWidth(1)
        vsep.setFixedWidth(1)
        content.addWidget(vsep)

        # Right: options panel
        right = QVBoxLayout()
        right.setSpacing(8)
        content.addLayout(right, 1)

        # Segmented kind selector
        seg_row = QHBoxLayout()
        seg_row.setSpacing(6)
        self.btn_audio = QPushButton("Audio")
        self.btn_audio.setCheckable(True)
        self.btn_audio.setObjectName("SegmentButton")
        self.btn_video = QPushButton("Video")
        self.btn_video.setCheckable(True)
        self.btn_video.setObjectName("SegmentButton")
        self.kind_group = QButtonGroup(self)
        self.kind_group.setExclusive(True)
        self.kind_group.addButton(self.btn_audio)
        self.kind_group.addButton(self.btn_video)
        if self.settings.defaults.kind == "audio":
            self.btn_audio.setChecked(True)
        else:
            self.btn_video.setChecked(True)
        seg_row.addWidget(self.btn_audio)
        seg_row.addWidget(self.btn_video)
        seg_row.addStretch(1)
        right.addLayout(seg_row)

        # Format
        self.cmb_format = QComboBox()
        self.cmb_format.setEditable(False)
        right.addWidget(self._labeled("Format:", self.cmb_format))

        # Quality
        self.cmb_quality = QComboBox()
        right.addWidget(self._labeled("Quality:", self.cmb_quality))

        right.addStretch(1)

        # Footer bar with Back (left) and Next (right) - consistent across steps
        footer = QHBoxLayout()
        # add a top separator line via a QFrame
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(sep)
        self.btn_back = QPushButton("Back")
        self.btn_next = QPushButton("Next")
        self.btn_next.setObjectName("PrimaryButton")
        footer.addWidget(self.btn_back)
        footer.addStretch(1)
        footer.addWidget(self.btn_next)
        root.addLayout(footer)

        # Defaults
        self._apply_kind_defaults()

        # Signals
        self.btn_back.clicked.connect(self.backRequested.emit)
        self.btn_next.clicked.connect(self._confirm)
        self.btn_audio.toggled.connect(self._kind_toggled)

        # Timer (kept but unused for background refetch)
        self._refetch_timer = QTimer(self)
        self._refetch_timer.setSingleShot(True)
        self._refetch_timer.timeout.connect(self._start_refetch_missing)

        # NEW: block mouse wheel on comboboxes to avoid accidental changes
        class _NoWheelFilter(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Wheel:
                    return True
                return super().eventFilter(obj, event)

        self._nowheel = _NoWheelFilter(self)
        for w in (self.cmb_format, self.cmb_quality):
            w.installEventFilter(self._nowheel)

    def _labeled(self, text: str, w: QWidget) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lab = QLabel(text)
        lay.addWidget(lab)
        lay.addWidget(w, 1)
        return row

    def _apply_kind_defaults(self):
        # Populate format choices based on kind
        if self.btn_audio.isChecked():
            self.cmb_format.clear()
            self.cmb_format.addItems(["mp3", "m4a", "flac", "wav", "opus"])
        else:
            self.cmb_format.clear()
            self.cmb_format.addItems(["mp4", "mkv", "webm"])
        self.cmb_format.setCurrentText(self.settings.defaults.format)
        self._populate_quality_options()

    def set_items(self, items: List[Dict]):
        self.items = items
        self._url_index = {}
        for i, it in enumerate(items):
            u = it.get("webpage_url") or it.get("url")
            if u:
                self._url_index[u] = i

        self.header.setText(
            f"Selected {len(items)} item(s). Choose output format and quality."
        )
        self.preview.clear()
        for it in items:
            title = it.get("title") or "Untitled"
            lw = QListWidgetItem(title)
            pix = self._load_thumb(it)
            if pix:
                lw.setIcon(QIcon(pix))
            self.preview.addItem(lw)

        # Fade-in transition for a clean update
        eff = QGraphicsOpacityEffect(self.preview)
        self.preview.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)

        # REMOVE height constraints so list fills and scrolls naturally
        # if len(items) <= 1:
        #     self.preview.setFixedHeight(self.preview.iconSize().height() + 16)
        # else:
        #     self.preview.setMinimumHeight(120)
        #     self.preview.setMaximumHeight(220)

        self._populate_quality_options()
        self._cleanup_fetchers()
        if hasattr(self, "_refetch_timer"):
            self._refetch_timer.stop()

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

    def _kind_toggled(self, audio_checked: bool):
        self._apply_kind_defaults()

    def _has_formats(self, it: Dict) -> bool:
        fmts = it.get("formats")
        return bool(fmts and isinstance(fmts, list) and len(fmts) > 0)

    def _populate_quality_options(self):
        self.cmb_quality.clear()
        default_v = ["best", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
        default_a = ["best", "320k", "256k", "192k", "160k", "128k"]

        if not self.items:
            self.cmb_quality.addItems(
                default_a if self.btn_audio.isChecked() else default_v
            )
            return

        # Single-item special handling
        if len(self.items) == 1 and not self._has_formats(self.items[0]):
            self.cmb_quality.addItems(["best", "worse"])
            return

        fmts_lists = [
            it.get("formats") or [] for it in self.items if self._has_formats(it)
        ]
        if self.btn_audio.isChecked():
            abrs = sorted(
                {
                    int(f.get("abr"))
                    for fmts in fmts_lists
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
                    for fmts in fmts_lists
                    for f in fmts
                    if f.get("height") and f.get("vcodec") != "none"
                },
                reverse=True,
            )
            opts = ["best"] + [f"{h}p" for h in heights] if heights else default_v
            self.cmb_quality.addItems(opts)

    def _start_refetch_missing(self):
        # disabled background refetching
        self._cleanup_fetchers()
        return

    def _cleanup_fetchers(self):
        for f in self._meta_fetchers:
            try:
                f.finished_ok.disconnect()
            except Exception:
                pass
            try:
                f.finished_fail.disconnect()
            except Exception:
                pass
        self._meta_fetchers.clear()

    def _confirm(self):
        if hasattr(self, "_refetch_timer"):
            self._refetch_timer.stop()
        self._cleanup_fetchers()
        kind = "audio" if self.btn_audio.isChecked() else "video"
        fmt = self.cmb_format.currentText().strip()
        quality = self.cmb_quality.currentText().strip() or "best"
        self.settings.defaults.kind = kind
        self.settings.defaults.format = fmt
        SettingsManager().save(self.settings)
        self.qualityConfirmed.emit(
            {"items": self.items, "kind": kind, "format": fmt, "quality": quality}
        )
