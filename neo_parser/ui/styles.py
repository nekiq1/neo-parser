"""Neo Parser visual system: graphite surfaces, restrained neon accents."""

DARK_STYLE = r"""
* { font-family: 'Segoe UI', 'Inter', Arial; font-size: 13px; }
QWidget { background: #0b0f17; color: #e8eef8; }
QMainWindow, QDialog { background: #090d14; }
QFrame#Sidebar { background: #0e1420; border: 1px solid #1e2b3c; border-radius: 20px; }
QFrame#Card { background: #111a28; border: 1px solid #24364b; border-radius: 17px; }
QFrame#Hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #14243a, stop:0.55 #111a2a, stop:1 #102b32); border: 1px solid #24516a; border-radius: 20px; }
QFrame#MetricCard { background: #111a28; border: 1px solid #263a50; border-radius: 16px; }
QFrame#MetricCard:hover { border: 1px solid #2c9eb0; background: #142235; }
QLabel#Brand { font-size: 21px; font-weight: 900; color: #f4f8ff; letter-spacing: 1px; }
QLabel#BrandAccent { color: #43d9d0; font-size: 10px; font-weight: 800; letter-spacing: 2px; }
QLabel#Muted { color: #8797ad; }
QLabel#SectionTitle { font-size: 25px; font-weight: 800; color: #f4f7fc; }
QLabel#SectionSubtitle { color: #91a2b8; font-size: 13px; }
QLabel#CardValue { font-size: 29px; font-weight: 900; color: #f4f8ff; }
QLabel#CardLabel { color: #9babc0; font-size: 12px; font-weight: 600; }
QLabel#MetricAccent { color: #4ce0d2; font-size: 11px; font-weight: 700; }
QLabel#HeroTitle { font-size: 22px; font-weight: 800; color: white; }
QLabel#HeroText { color: #a9bfd1; font-size: 13px; }
QPushButton { background: #172336; border: 1px solid #2a3d55; border-radius: 11px; padding: 10px 16px; color: #e5edf8; font-weight: 600; }
QPushButton:hover { background: #1d3047; border: 1px solid #368b9b; color: white; }
QPushButton:pressed { background: #122c3b; border: 1px solid #43d9d0; }
QPushButton:disabled { color: #5b687a; background: #131b28; border-color: #202c3d; }
QPushButton#Primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #167d91, stop:1 #2563b8); border: 1px solid #3ba9b7; color: white; font-weight: 800; }
QPushButton#Primary:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1999a8, stop:1 #347de0); border: 1px solid #6debe0; }
QPushButton#Primary:pressed { background: #145d75; }
QPushButton#Danger { background: #321d2b; border: 1px solid #65344b; color: #ff9db6; }
QPushButton#Nav, QPushButton#NavActive { text-align: left; padding: 12px 14px; border: 1px solid transparent; background: transparent; border-radius: 11px; color: #9eacc0; font-weight: 600; }
QPushButton#Nav:hover { background: #162337; color: #effaff; border-color: #263e56; }
QPushButton#NavActive { background: #142c3a; border: 1px solid #24596a; color: #65e6dc; font-weight: 800; }
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit, QListWidget { background: #101a29; border: 1px solid #293b52; border-radius: 10px; padding: 9px 12px; color: #e8eef8; selection-background-color: #176f86; }
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus { border: 1px solid #42c9c6; }
QComboBox::drop-down { border: 0; width: 28px; }
QComboBox QAbstractItemView { background: #111b2a; border: 1px solid #2a405a; selection-background-color: #1d5265; color: #eef5ff; }
QCheckBox { spacing: 8px; color: #b8c5d6; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 5px; border: 1px solid #49617a; background: #101a29; }
QCheckBox::indicator:checked { background: #27a6a5; border: 1px solid #62e9dd; }
QTableWidget { background: #0f1825; alternate-background-color: #121e2e; border: 1px solid #26394f; border-radius: 14px; gridline-color: #1d2d40; outline: 0; }
QTableWidget::item { padding: 8px; }
QTableWidget::item:selected { background: #194357; color: white; }
QHeaderView::section { background: #162336; color: #aebed2; padding: 11px 8px; border: 0; border-bottom: 1px solid #2b4058; font-weight: 800; }
QProgressBar { background: #1b2a3d; border: 1px solid #2c415a; border-radius: 7px; height: 12px; text-align: center; color: #e8f7ff; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #25c5ba, stop:1 #367be0); border-radius: 6px; }
QStatusBar { background: #0a1019; color: #92a4bb; border-top: 1px solid #1b2b3e; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: #2b4058; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3c7180; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #17263a; color: #f0f6ff; border: 1px solid #3d697c; padding: 7px; }
"""
