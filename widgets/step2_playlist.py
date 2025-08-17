from typing import List, Dict
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QCheckBox,
)
from PyQt6.QtGui import QIcon, QPixmap, QImage

ICON_PIXMAP_ROLE = int(Qt.ItemDataRole.UserRole) + 1


class Step2PlaylistWidget(QWidget):
    selectionConfirmed = pyqtSignal(list)
    backRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(6)

        # Top info label
        self.lbl = QLabel("")
        self.lbl.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        lay.addWidget(self.lbl)

        # Controls row
        top = QHBoxLayout()
        self.btn_back = QPushButton("Back")
        self.chk_all = QCheckBox("Select All")
        self.btn_next = QPushButton("Next")
        top.addWidget(self.btn_back)
        top.addWidget(self.chk_all)
        top.addStretch(1)
        top.addWidget(self.btn_next)
        lay.addLayout(top)

        self.list = QListWidget()
        self.list.setIconSize(QSize(96, 54))
        lay.addWidget(self.list, 1)

        self.btn_back.clicked.connect(self.backRequested.emit)
        self.chk_all.stateChanged.connect(self._toggle_all)
        self.btn_next.clicked.connect(self._confirm)
        self.list.itemChanged.connect(self._on_item_changed)  # NEW

    def set_entries(self, entries: List[Dict]):
        self.list.clear()
        for e in entries or []:
            title = e.get("title") or "Untitled"
            it = QListWidgetItem(title)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            it.setData(Qt.ItemDataRole.UserRole, e)
            pix = self._load_thumb(e)
            if pix:
                it.setIcon(QIcon(pix))
                it.setData(ICON_PIXMAP_ROLE, pix)
            self.list.addItem(it)
            self._apply_item_style(it)  # ensure correct initial icon
        self._update_selected_label()

    def _load_thumb(self, e: Dict):
        url = e.get("thumbnail") or (e.get("thumbnails") or [{}])[-1].get("url")
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

    def _to_gray(self, pix: QPixmap) -> QPixmap:
        try:
            img = pix.toImage().convertToFormat(QImage.Format.Format_Grayscale8)
            return QPixmap.fromImage(img)
        except Exception:
            return pix

    def _apply_item_style(self, it: QListWidgetItem):
        pix = it.data(ICON_PIXMAP_ROLE)
        if not isinstance(pix, QPixmap):
            return
        if it.checkState() == Qt.CheckState.Checked:
            it.setIcon(QIcon(pix))
        else:
            it.setIcon(QIcon(self._to_gray(pix)))

    def _on_item_changed(self, it: QListWidgetItem):
        self._apply_item_style(it)
        self._update_selected_label()

    def _toggle_all(self, state):
        check = (
            Qt.CheckState.Checked
            if state == Qt.CheckState.Checked
            else Qt.CheckState.Unchecked
        )
        self.list.blockSignals(True)  # avoid per-item itemChanged storms
        for i in range(self.list.count()):
            it = self.list.item(i)
            it.setCheckState(check)
            self._apply_item_style(it)
        self.list.blockSignals(False)
        self._update_selected_label()

    def _update_selected_label(self):
        count = sum(
            1
            for i in range(self.list.count())
            if self.list.item(i).checkState() == Qt.CheckState.Checked
        )
        self.lbl.setText(f"Selected {count} item(s)")

    def _confirm(self):
        out = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        self.selectionConfirmed.emit(out)
