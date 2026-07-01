from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)

from ui.theme import COLORS


class MessageBubble(QWidget):

    def __init__(self, role: str, text: str):
        super().__init__()

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        bubble = QFrame()
        bubble.setMaximumWidth(520)

        if role == "user":
            bubble_color = COLORS["primary"]
            outer.addStretch()
            outer.addWidget(bubble)
        else:
            bubble_color = COLORS["surface_light"]
            outer.addWidget(bubble)
            outer.addStretch()

        bubble.setStyleSheet(f"""
        QFrame {{
            background:{bubble_color};
            border-radius:14px;
            border:1px solid {COLORS["border"]};
        }}

        QLabel {{
            background:transparent;
            color:{COLORS["text"]};
        }}
        """)

        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("👤 You" if role == "user" else "🤖 Sidekick AI")
        title.setStyleSheet("""
            font-weight:700;
            font-size:11pt;
        """)

        message = QLabel(text)
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        message.setStyleSheet("""
            font-size:10.5pt;
        """)

        layout.addWidget(title)
        layout.addWidget(message)