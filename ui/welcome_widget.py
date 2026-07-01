from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)

from ui.theme import COLORS


class WelcomeWidget(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("welcomeCard")

        self.setStyleSheet(f"""
        QFrame#welcomeCard {{
            background:{COLORS["surface_light"]};
            border-radius:18px;
            border:1px solid {COLORS["border"]};
        }}

        QLabel {{
            background:transparent;
            color:{COLORS["text"]};
        }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)

        title = QLabel("🤖 Sidekick AI")
        title.setStyleSheet("""
            font-size:18px;
            font-weight:700;
        """)

        subtitle = QLabel(
            "Your intelligent desktop AI companion powered by MCP."
        )
        subtitle.setWordWrap(True)

        section = QLabel("Try asking:")
        section.setStyleSheet("font-weight:600;")

        examples = QLabel(
            "📄 Explain this project\n\n"
            "📁 Find app.py\n\n"
            "📧 Draft an email\n\n"
            "👥 Open Teams\n\n"
            "🌐 Open Browser"
        )

        examples.setAlignment(Qt.AlignLeft)

        footer = QLabel("Ready when you are.")
        footer.setStyleSheet(f"color:{COLORS['text_secondary']};")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(10)
        layout.addWidget(section)
        layout.addWidget(examples)
        layout.addStretch()
        layout.addWidget(footer)