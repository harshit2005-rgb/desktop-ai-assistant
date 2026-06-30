from PySide6.QtWidgets import (
    QFrame,
    QTextBrowser,
    QVBoxLayout,
)

from ui.theme import COLORS


class ChatWidget(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("chatCard")

        self.setStyleSheet(f"""
        QFrame#chatCard {{
            background:{COLORS["surface"]};
            border-radius:12px;
        }}

        QTextBrowser {{
            border:none;
            background:transparent;
            color:{COLORS["text"]};
            padding:12px;
            font-size:11pt;
        }}
        """)

        layout = QVBoxLayout(self)

        self.chat = QTextBrowser()

        layout.addWidget(self.chat)

        self.append_assistant(
            "👋 Welcome to <b>Sidekick AI</b><br><br>"
            "I'm your desktop AI companion powered by MCP.<br><br>"
            "I can help you with:<br>"
            "• 📁 File Management<br>"
            "• 📧 Gmail<br>"
            "• 👥 Microsoft Teams<br>"
            "• 🌐 Browser Automation<br>"
            "• 📄 PDF Analysis<br>"
            "• 💻 Project Understanding"
        )

    def append_user(self, text: str):
        self.chat.append(
            f"""
            <div style="
                background:#2E2E2E;
                padding:10px;
                border-radius:10px;
                margin:8px;
            ">
            👤 <b>You</b><br><br>
            {text}
            </div>
            """
        )

    def append_assistant(self, text: str):
        self.chat.append(
            f"""
            <div style="
                background:#1F2937;
                padding:10px;
                border-radius:10px;
                margin:8px;
            ">
            🤖 <b>Sidekick AI</b><br><br>
            {text}
            </div>
            """
        )