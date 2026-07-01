from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from ui.activity_indicator import ActivityIndicator
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

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.title = QLabel("🤖 Sidekick AI")
        self.title.setStyleSheet("""
            font-size:18px;
            font-weight:700;
        """)
        self.title.setAlignment(Qt.AlignVCenter)

        self.activity_indicator = ActivityIndicator(self)
        self.activity_indicator.setObjectName("activityIndicator")

        title_row.addWidget(self.title)
        title_row.addStretch()
        title_row.addWidget(self.activity_indicator)

        layout.addLayout(title_row)

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
        self.stop_activity()
        self.status.setText("Ready • Groq • 7 MCP Servers")

    def set_thinking(self):
        self.start_activity()
        self.status.setText("Thinking...")
        QApplication.processEvents()

    def set_working(self, tool: str):
        self.start_activity()
        print("STATUS:", tool)
        self.status.setText(f"Using {tool}")
        QApplication.processEvents()

    def set_error(self, message="Something went wrong"):
        self.stop_activity()
        self.status.setText(message)

    def start_activity(self):
        self.activity_indicator.start_activity()

    def stop_activity(self):
        self.activity_indicator.stop_activity() 