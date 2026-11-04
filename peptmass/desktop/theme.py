"""Folhas de estilo dos temas escuro e claro."""
DARK_QSS = """
* { font-family: 'Segoe UI', 'Helvetica Neue', Arial; font-size: 10pt; }
QMainWindow, QWidget { background: #1e2228; color: #e6e9ef; }
QGroupBox { border: 1px solid #333a44; border-radius: 7px; margin-top: 10px;
            padding-top: 8px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px;
                   color: #8fb4ff; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #262b33; border: 1px solid #3a414d; border-radius: 5px;
    padding: 5px; color: #e6e9ef; selection-background-color: #3d6fd6; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #5b8bff; }
QPushButton { background: #2f3640; border: 1px solid #424b58; border-radius: 6px;
              padding: 7px 14px; color: #e6e9ef; }
QPushButton:hover { background: #3a4250; }
QPushButton:pressed { background: #2a303a; }
QPushButton#accent { background: #3d6fd6; border: none; font-weight: 600; }
QPushButton#accent:hover { background: #4d7fe6; }
QTabWidget::pane { border: 1px solid #333a44; border-radius: 6px; }
QTabBar::tab { background: #262b33; padding: 9px 18px; border-top-left-radius: 6px;
               border-top-right-radius: 6px; color: #aeb6c2; margin-right: 2px; }
QTabBar::tab:selected { background: #3d6fd6; color: white; font-weight: 600; }
QTableWidget { background: #20252c; gridline-color: #2f3640;
               border: 1px solid #333a44; border-radius: 6px; }
QHeaderView::section { background: #2c333d; color: #cfd6e2; padding: 6px;
                       border: none; border-right: 1px solid #1e2228;
                       font-weight: 600; }
QTableWidget::item:selected { background: #3d6fd6; color: white; }
QCheckBox { spacing: 6px; }
QLabel#result { font-size: 15pt; font-weight: 700; color: #7fe3a0; }
QLabel#resultavg { font-size: 13pt; font-weight: 600; color: #f0c674; }
QLabel#formula { font-size: 11pt; color: #8fb4ff; font-family: monospace; }
QStatusBar { background: #181c22; color: #8a93a0; }
QToolBar { background: #181c22; border: none; spacing: 4px; padding: 4px; }
QScrollArea { border: none; }
"""

LIGHT_QSS = """
* { font-family: 'Segoe UI', 'Helvetica Neue', Arial; font-size: 10pt; }
QMainWindow, QWidget { background: #f4f6f9; color: #1f2733; }
QGroupBox { border: 1px solid #d4dae3; border-radius: 7px; margin-top: 10px;
            padding-top: 8px; font-weight: 600; background: #ffffff; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px;
                   color: #2c5fb8; }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff; border: 1px solid #ccd4de; border-radius: 5px;
    padding: 5px; color: #1f2733; selection-background-color: #cfe0ff; }
QLineEdit:focus, QPlainTextEdit:focus { border: 1px solid #2c5fb8; }
QPushButton { background: #ffffff; border: 1px solid #ccd4de; border-radius: 6px;
              padding: 7px 14px; }
QPushButton:hover { background: #eef2f8; }
QPushButton#accent { background: #2c5fb8; border: none; color: white;
                     font-weight: 600; }
QPushButton#accent:hover { background: #3a6fc8; }
QTabWidget::pane { border: 1px solid #d4dae3; border-radius: 6px;
                   background: #ffffff; }
QTabBar::tab { background: #e6ebf2; padding: 9px 18px; border-top-left-radius: 6px;
               border-top-right-radius: 6px; color: #5a6473; margin-right: 2px; }
QTabBar::tab:selected { background: #2c5fb8; color: white; font-weight: 600; }
QTableWidget { background: #ffffff; gridline-color: #e3e8ef;
               border: 1px solid #d4dae3; border-radius: 6px; }
QHeaderView::section { background: #eef2f8; color: #3a4757; padding: 6px;
                       border: none; border-right: 1px solid #d4dae3;
                       font-weight: 600; }
QTableWidget::item:selected { background: #cfe0ff; color: #1f2733; }
QLabel#result { font-size: 15pt; font-weight: 700; color: #1a7f3c; }
QLabel#resultavg { font-size: 13pt; font-weight: 600; color: #b5811a; }
QLabel#formula { font-size: 11pt; color: #2c5fb8; font-family: monospace; }
QStatusBar { background: #e6ebf2; color: #5a6473; }
QToolBar { background: #e6ebf2; border: none; spacing: 4px; padding: 4px; }
QScrollArea { border: none; }
"""
