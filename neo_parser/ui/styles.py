DARK_STYLE = """
QWidget {
    background: #10131a;
    color: #e8edf5;
    font-family: 'Segoe UI', 'Inter', system-ui, Arial;
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #0d1017;
}
QFrame#Sidebar {
    background: #141922;
    border: 1px solid #242c3a;
    border-radius: 16px;
}
QFrame#Card {
    background: #171c26;
    border: 1px solid #2a3444;
    border-radius: 14px;
}
QLabel#Brand {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: 0.5px;
}
QLabel#Muted {
    color: #8995a8;
}
QLabel#SectionTitle {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#CardValue {
    font-size: 26px;
    font-weight: 800;
    color: #ffffff;
}
QLabel#CardLabel {
    color: #8995a8;
    font-size: 12px;
}
QPushButton {
    background: #202938;
    border: 1px solid #303d50;
    border-radius: 9px;
    padding: 9px 16px;
    color: #e8edf5;
}
QPushButton:hover {
    background: #2a384d;
}
QPushButton:disabled {
    color: #5a6578;
    background: #1a2030;
}
QPushButton#Primary {
    background: #3b82f6;
    border: 0;
    font-weight: 700;
    color: #ffffff;
}
QPushButton#Primary:hover {
    background: #60a5fa;
}
QPushButton#Danger {
    background: #3a1f2a;
    border: 1px solid #5c2b3a;
    color: #f5a3b5;
}
QPushButton#Nav {
    text-align: left;
    padding: 11px 14px;
    border: 0;
    background: transparent;
    border-radius: 10px;
    color: #aebbd0;
}
QPushButton#Nav:hover {
    background: #1e2636;
    color: #ffffff;
}
QPushButton#NavActive {
    text-align: left;
    padding: 11px 14px;
    border: 0;
    background: #243044;
    border-radius: 10px;
    color: #ffffff;
    font-weight: 600;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {
    background: #171e2a;
    border: 1px solid #30394a;
    border-radius: 9px;
    padding: 9px 12px;
    selection-background-color: #3b82f6;
    color: #e8edf5;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QComboBox QAbstractItemView {
    background: #171e2a;
    border: 1px solid #30394a;
    selection-background-color: #3b82f6;
}
QTableWidget {
    background: #151b25;
    alternate-background-color: #192230;
    border: 1px solid #2a3444;
    border-radius: 12px;
    gridline-color: #263142;
    outline: 0;
}
QTableWidget::item {
    padding: 6px;
}
QTableWidget::item:selected {
    background: #2a3a55;
    color: #ffffff;
}
QHeaderView::section {
    background: #1c2433;
    color: #aebbd0;
    padding: 10px 8px;
    border: 0;
    border-bottom: 1px solid #2a3444;
    font-weight: 600;
}
QProgressBar {
    background: #202938;
    border: 0;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    color: #c5d0e0;
}
QProgressBar::chunk {
    background: #3b82f6;
    border-radius: 6px;
}
QStatusBar {
    background: #0d1017;
    color: #8995a8;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #303d50;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QTabWidget::pane {
    border: 1px solid #2a3444;
    border-radius: 10px;
}
QListWidget {
    background: #151b25;
    border: 1px solid #2a3444;
    border-radius: 10px;
    outline: 0;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background: #2a3a55;
}
QToolTip {
    background: #1c2433;
    color: #e8edf5;
    border: 1px solid #303d50;
    padding: 6px;
}
"""
