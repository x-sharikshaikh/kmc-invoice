from PySide6.QtWidgets import QApplication
from .ui_main import create_main_window


def main() -> None:
    app = QApplication()
    win = create_main_window()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
