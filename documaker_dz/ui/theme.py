"""Modern Arabic-first PySide6 QSS theme for DocuMaker DZ."""

APP_QSS = """
QMainWindow, QWidget {
    background-color: #0B111E;
    color: #F1F5F9;
    font-family: "Segoe UI", "Tahoma", "Cairo", sans-serif;
    font-size: 13px;
}

QFrame#Sidebar {
    background-color: #0F172A;
    border-left: 1px solid #1E293B;
    border-right: 1px solid #1E293B;
}

QLabel#BrandTitle {
    font-size: 18px;
    font-weight: 700;
    color: #34D399;
}

QLabel#BrandSub {
    font-size: 11px;
    color: #94A3B8;
}

QLabel#PageTitle {
    font-size: 20px;
    font-weight: 700;
    color: #F8FAFC;
    padding-bottom: 4px;
}

QLabel#PageSub {
    font-size: 13px;
    color: #94A3B8;
}

QPushButton#NavBtn {
    text-align: right;
    padding: 11px 14px;
    border-radius: 8px;
    background-color: transparent;
    color: #CBD5E1;
    border: none;
    font-weight: 600;
}

QPushButton#NavBtn:hover {
    background-color: #1E293B;
    color: #FFFFFF;
}

QPushButton#NavBtn[active="true"] {
    background-color: #064E3B;
    color: #34D399;
    border: 1px solid #059669;
}

QFrame#Card {
    background-color: #111827;
    border: 1px solid #1F2937;
    border-radius: 12px;
}

QFrame#WarnBanner {
    background-color: #2A1F0D;
    border: 1px solid #D97706;
    border-radius: 8px;
    padding: 8px;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 10px;
    color: #F8FAFC;
    selection-background-color: #059669;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1px solid #34D399;
}

QPushButton#PrimaryBtn {
    background-color: #059669;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 11px 20px;
    font-weight: 700;
    font-size: 14px;
}

QPushButton#PrimaryBtn:hover {
    background-color: #10B981;
}

QPushButton#PrimaryBtn:disabled {
    background-color: #1E293B;
    color: #64748B;
}

QPushButton#SecondaryBtn {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}

QPushButton#SecondaryBtn:hover {
    background-color: #334155;
}

QPushButton#DangerBtn {
    background-color: #7F1D1D;
    color: #FEE2E2;
    border: 1px solid #B91C1C;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: 600;
}

QPushButton#DangerBtn:hover {
    background-color: #991B1B;
}

QProgressBar {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: #E2E8F0;
}

QProgressBar::chunk {
    background-color: #10B981;
    border-radius: 5px;
}

QTabWidget::pane {
    border: 1px solid #1F2937;
    border-radius: 10px;
    background-color: #111827;
    padding: 10px;
}

QTabBar::tab {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 8px 14px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-left: 3px;
}

QTabBar::tab:selected {
    background-color: #1E293B;
    color: #34D399;
    font-weight: 700;
}

QScrollArea {
    border: none;
    background: transparent;
}
"""
