from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QApplication,
)

from services.agent_service import AgentService

from ui.header_widget import HeaderWidget
from ui.quick_actions import QuickActionsWidget
from ui.chat_widget import ChatWidget
from ui.input_widget import InputWidget
from ui.welcome_widget import WelcomeWidget

from ui.theme import (
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    app_stylesheet,
)


class SidekickWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("🤖 Sidekick AI")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setStyleSheet(app_stylesheet())

        self.build_ui()

        self.agent = AgentService(
            on_status=self.header.set_working
        )


    def build_ui(self):

        self.layout = QVBoxLayout(self)

        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(8)

        # Header
        self.header = HeaderWidget()
        self.layout.addWidget(self.header)

        # Quick Actions
        self.quick_actions = QuickActionsWidget()
        self.layout.addWidget(self.quick_actions)

        # Welcome Card
        self.welcome = WelcomeWidget()
        self.layout.addWidget(self.welcome, 1)

        # Chat (hidden initially)
        self.chat = ChatWidget()
        self.chat.hide()
        self.layout.addWidget(self.chat, 1)

        # Input
        self.input = InputWidget()
        self.layout.addWidget(self.input)

        # Connections
        self.input.messageSubmitted.connect(
            self.handle_user_message
        )

        self.quick_actions.actionTriggered.connect(
            self.handle_user_message
        )

    def handle_user_message(self, message: str):

        if not message.strip():
            return

        # First message switches from Welcome -> Chat
        if self.welcome.isVisible():

            self.welcome.hide()

            self.quick_actions.hide()

            self.chat.show()

            self.chat.clear_chat()

        self.chat.add_user_message(message)

        self.header.set_thinking()

        QApplication.processEvents()

        try:

            result = self.agent.handle_message(message)

            self.chat.add_assistant_message(
                result.assistant_message
            )

            self.header.set_ready()

            self.input.input.setFocus()

        except Exception as e:

            self.chat.add_assistant_message(
                f"❌ {e}"
            )

            self.header.set_error()