from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
)

from ui.theme import COLORS


class HeaderWidget(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName("headerCard")

        self.setStyleSheet(f"""
        QFrame#headerCard {{
            background-color: {COLORS["surface"]};
            border-radius: 12px;
            padding: 8px;
        }}

        QLabel {{
            color: {COLORS["text"]};
            background: transparent;
        }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        title = QLabel("🤖 Sidekick AI")
        title.setStyleSheet("""
            font-size:18px;
            font-weight:700;
        """)

        root.addWidget(title)

        status = QHBoxLayout()

        ready = QLabel("🟢 Ready")
        provider = QLabel("Groq")
        mcp = QLabel("7 MCP Servers")
        memory = QLabel("Memory ✓")

        status.addWidget(ready)
        status.addStretch()
        status.addWidget(provider)
        status.addStretch()
        status.addWidget(mcp)
        status.addStretch()
        status.addWidget(memory)

        root.addLayout(status)