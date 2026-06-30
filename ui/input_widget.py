from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
)

from ui.theme import COLORS


class InputWidget(QWidget):

    messageSubmitted = Signal(str)

    def __init__(self):
        super().__init__()

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0, 0, 0, 0)

        layout.setSpacing(10)

        self.input = QLineEdit()

        self.input.setPlaceholderText(
            "Ask Sidekick AI..."
        )

        self.send = QPushButton("➜")

        layout.addWidget(self.input)

        layout.addWidget(self.send)

        self.send.clicked.connect(self.submit)

        self.input.returnPressed.connect(self.submit)

    def submit(self):

        text = self.input.text().strip()

        if not text:
            return

        self.messageSubmitted.emit(text)

        self.input.clear()