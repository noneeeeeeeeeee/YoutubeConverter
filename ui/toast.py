from PyQt6.QtCore import Qt, QTimer, QPoint, QEasingCurve, QPropertyAnimation
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtWidgets import QGraphicsOpacityEffect


class Toast(QWidget):
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.lbl = QLabel("", self)
        self.lbl.setStyleSheet(
            """
            background: rgba(30,30,30,220);
            color: white;
            padding: 10px 14px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,30);
        """
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.addWidget(self.lbl)

        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.anim_in = QPropertyAnimation(self.opacity, b"opacity", self)
        self.anim_in.setDuration(150)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.anim_out = QPropertyAnimation(self.opacity, b"opacity", self)
        self.anim_out.setDuration(200)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim_out.finished.connect(super().hide)

        self.timer = QTimer(self)
        self.timer.setInterval(2500)
        self.timer.timeout.connect(self._fade_out)

    def show_message(self, text: str):
        self.lbl.setText(text)
        self.adjustSize()
        self._reposition()
        self.opacity.setOpacity(0.0)
        super().show()
        self.raise_()
        self.anim_in.start()
        self.timer.start()

    def _fade_out(self):
        self.timer.stop()
        self.anim_out.start()

    def _reposition(self):
        if not self.parent():
            return
        parent = self.parent().window()
        geo = parent.geometry()
        g = self.frameGeometry()
        x = geo.x() + geo.width() - g.width() - 24
        y = geo.y() + geo.height() - g.height() - 24
        self.move(x, y)


class ToastManager:
    def __init__(self, parent):
        self.toast = Toast(parent)

    def show(self, text: str):
        self.toast.show_message(text)
