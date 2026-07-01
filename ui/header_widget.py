from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)

from ui.theme import COLORS
from PySide6.QtWidgets import QApplication


class HeaderWidget(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("headerCard")

        self.setStyleSheet(f"""
        QFrame#headerCard {{
            background:{COLORS["surface"]};
            border-radius:14px;
            border:1px solid {COLORS["border"]};
        }}

        QLabel {{
            background:transparent;
            color:{COLORS["text"]};
        }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        self.title = QLabel("🤖 Sidekick AI")
        self.title.setStyleSheet("""
            font-size:18px;
            font-weight:700;
        """)

        layout.addWidget(self.title)

        self.status = QLabel()
        self.status.setStyleSheet("""
            color:#A8A8A8;
            font-size:11px;
        """)

        layout.addWidget(self.status)

        self.set_ready()

    # -----------------------------
    # States
    # -----------------------------

    def set_ready(self):
        self.status.setText(
            "🟢 Ready • Groq • 7 MCP Servers"
        )

    def set_thinking(self):
        self.status.setText("🔵 Thinking...")
        QApplication.processEvents()

    def set_working(self, tool: str):
        print("STATUS:", tool)
        self.status.setText(f"⚡ Using {tool}")
        QApplication.processEvents()

    def set_error(self, message="Something went wrong"):
        self.status.setText(f"🔴 {message}") 