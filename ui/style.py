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
QPushButton:hover {{ border-color: {ac}; }}
QPushButton:pressed {{ background: #25262a; }}
/* Toggle state */
QPushButton:checked {{
    border-color: {ac};
    background: #2d2e33;
}}
/* Remove focus outline */
QPushButton:focus, QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
    outline: 0; border: 1px solid #34353b;
}}
QPushButton#IconButton {{ font-size: 18px; padding: 0; }}
QLineEdit, QComboBox, QTextEdit {{
    background: #222327; border: 1px solid #34353b; border-radius: 8px; padding: 6px 8px;
}}
/* Win11-like CheckBox indicator (default checkboxes) */
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 2px solid #5a5b61;
    border-radius: 5px;
    background: #2a2b30;
    margin-right: 6px;
}}
QCheckBox::indicator:hover {{ border-color: {ac}; }}
QCheckBox::indicator:checked {{
    border-color: {ac};
    background: #2a2b30;
    image: url(:/qt-project.org/styles/commonstyle/images/checkboxindicatorcheck.png);
}}
/* Button-like checkbox (used for 'Add multiple') */
QCheckBox#ButtonLike {{
    background: #2a2b30;
    border: 1px solid #33343a;
    border-radius: 8px;
    padding: 8px 12px;
}}
QCheckBox#ButtonLike:hover {{ border-color: {ac}; }}
QCheckBox#ButtonLike:checked {{
    border-color: {ac};
    background: #2d2e33;
}}
QCheckBox#ButtonLike::indicator {{
    width: 0px; height: 0px; /* hide default square */
}}
/* ProgressBar */
QProgressBar {{
    border: 1px solid #34353b; border-radius: 8px; background: #24252a; text-align: center;
}}
QProgressBar::chunk {{ background-color: {ac}; border-radius: 8px; }}
/* Scrollbars */
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: #3a3b41; min-height: 24px; border-radius: 6px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: {ac}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: #3a3b41; min-width: 24px; border-radius: 6px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: {ac}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ height: 0; width: 0; }}
QScrollBar::corner {{ background: transparent; }}
/* Tabs */
QTabWidget::pane {{
    border: 1px solid #34353b; border-radius: 10px; padding: 6px; top: -1px; background: #1f2024;
}}
QTabWidget::tab-bar {{ alignment: left; }}
QTabBar::tab {{
    background: #2a2b30; color: #e6e6e6; border: 1px solid transparent; border-bottom: none;
    padding: 8px 14px; margin-right: 6px; margin-top: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px;
}}
QTabBar::tab:selected {{ background: #24252a; color: {ac}; border-color: #34353b; margin-top: 0; }}
QTabBar::tab:hover {{ color: {ac}; }}
QTabBar::tear {{ width: 0; height: 0; }}
/* Stepper */
#StepperLabel {{
    background: #24252a; border: 1px solid #34353b; border-radius: 16px; padding: 6px 12px;
}}
#StepperLabel[current="true"] {{ border-color: {ac}; color: {ac}; }}
"""
