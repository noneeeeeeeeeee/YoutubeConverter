class StyleManager:
    def __init__(self, accent_hex: str):
        self._accent = accent_hex

    def with_accent(self, hex_color: str):
        self._accent = hex_color
        return self.qss()

    def qss(self) -> str:
        ac = self._accent
        return f"""
/* Base */
QWidget {{
    background: #1e1f22;
    color: #e6e6e6;
    font-size: 13px;
}}
QFrame#Sidebar {{
    background: #202125;
    border-right: 1px solid #2e2f33;
}}
QPushButton {{
    background: #2a2b30;
    border: 1px solid #33343a;
    border-radius: 8px;
    padding: 8px 12px;
}}
QPushButton:hover {{
    border-color: {ac};
}}
QPushButton:pressed {{
    background: #25262a;
}}
/* Remove focus dotted outlines by normalizing border on focus */
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    outline: 0;
    border: 1px solid #34353b;
}}
QPushButton#IconButton {{
    font-size: 18px;
    padding: 0;
}}
QLineEdit, QComboBox, QTextEdit {{
    background: #222327;
    border: 1px solid #34353b;
    border-radius: 8px;
    padding: 6px 8px;
}}
QCheckBox::indicator {{
    width: 18px; height: 18px;
}}
QCheckBox::indicator:checked {{
    background: {ac};
    border: 1px solid {ac};
}}
QProgressBar {{
    border: 1px solid #34353b;
    border-radius: 8px;
    background: #24252a;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {ac};
    border-radius: 8px;
}}
/* Windows 11-like Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #3a3b41;
    min-height: 24px;
    border-radius: 6px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ac};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    width: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: #3a3b41;
    min-width: 24px;
    border-radius: 6px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {ac};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    height: 0;
    width: 0;
}}
QScrollBar::corner {{
    background: transparent;
}}
/* Stepper */
#StepperLabel {{
    background: #24252a;
    border: 1px solid #34353b;
    border-radius: 16px;
    padding: 6px 12px;
}}
#StepperLabel[current="true"] {{
    border-color: {ac};
    color: {ac};
}}
"""
