from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel


class Stepper(QWidget):
    def __init__(self):
        super().__init__()
        self._labels = []
        self._current = 0
        self._steps = []
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 8, 8)
        self._layout.setSpacing(8)

    def set_steps(self, steps):
        # Clear
        for lab in self._labels:
            self._layout.removeWidget(lab)
            lab.deleteLater()
        self._labels.clear()
        self._steps = steps[:]
        for s in steps:
            lab = QLabel(s)
            lab.setObjectName("StepperLabel")
            lab.setProperty("current", False)
            lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(lab)
            self._labels.append(lab)
        self.set_current(0)

    def set_current(self, idx: int):
        self._current = max(0, min(idx, len(self._labels) - 1)) if self._labels else 0
        for i, lab in enumerate(self._labels):
            lab.setProperty("current", i == self._current)
            lab.style().unpolish(lab)
            lab.style().polish(lab)
