from PySide6.QtWidgets import (
    QFrame,
    QWidget,
    QVBoxLayout,
    QScrollArea,
)

from ui.theme import COLORS
from ui.message_bubble import MessageBubble


class ChatWidget(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("chatCard")

        self.setStyleSheet(f"""
        QFrame#chatCard {{
            background:#000000;
            border-radius:14px;
        }}

        QScrollArea {{
            border:none;
            background:transparent;
        }}

        QWidget {{
            background:transparent;
        }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)

        self.container = QWidget()

        self.messages = QVBoxLayout(self.container)
        self.messages.setContentsMargins(14, 14, 14, 14)
        self.messages.setSpacing(10)
        self.messages.addStretch()

        self.scroll.setWidget(self.container)

        root.addWidget(self.scroll)

        self.show_welcome()

    def _scroll_bottom(self):
        bar = self.scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _add(self, role, text):

        bubble = MessageBubble(role, text)

        self.messages.insertWidget(
            self.messages.count() - 1,
            bubble,
        )

        self._scroll_bottom()

    def show_welcome(self):

        while self.messages.count() > 1:

            item = self.messages.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        self._add(
            "assistant",
            """👋 Welcome to Sidekick AI

Your intelligent desktop companion powered by MCP.

I can help with:

• File Management
• Gmail
• Microsoft Teams
• Browser Automation
• PDF Analysis
• Project Understanding

Ask me anything."""
        )

    def add_user_message(self, text):
        self._add("user", text)

    def add_assistant_message(self, text):
        self._add("assistant", text)

    def clear_chat(self):
        self.show_welcome()