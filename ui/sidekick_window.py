from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QApplication,
)

from ui.header_widget import HeaderWidget
from ui.theme import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    app_stylesheet,
)
from ui.quick_actions import QuickActionsWidget
from ui.chat_widget import ChatWidget
from ui.input_widget import InputWidget


class SidekickWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("🤖 Sidekick AI")

        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.setStyleSheet(app_stylesheet())

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(16, 16, 16, 16)

        layout.setSpacing(16)

        self.header = HeaderWidget()

        layout.addWidget(self.header)

        self.quick_actions = QuickActionsWidget()
        
        layout.addWidget(self.quick_actions)

        self.chat = ChatWidget()

        layout.addWidget(self.chat, 1)

        self.input = InputWidget()

        layout.addWidget(self.input)