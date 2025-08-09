from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel


def create_main_window() -> QMainWindow:
    win = QMainWindow()
    win.setWindowTitle("KMC Invoice")
    central = QWidget()
    layout = QVBoxLayout(central)
    layout.addWidget(QLabel("KMC Invoice App Scaffold"))
    win.setCentralWidget(central)
    return win
