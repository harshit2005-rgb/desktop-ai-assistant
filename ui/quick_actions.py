from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QPushButton,
)

from ui.theme import COLORS


class QuickActionsWidget(QFrame):

    def __init__(self):
        super().__init__()

        self.setObjectName("quickCard")

        self.setStyleSheet(f"""
        QFrame#quickCard {{
            background:{COLORS["surface"]};
            border-radius:12px;
        }}

        QPushButton {{
            background:{COLORS["surface_light"]};
            border:none;
            border-radius:10px;
            padding:12px;
            text-align:left;
        }}

        QPushButton:hover {{
            background:{COLORS["primary_hover"]};
        }}
        """)

        layout = QGridLayout(self)

        actions = [
            "📄 Explain",
            "👥 Teams",
            "📧 Gmail",
            "📁 Files",
            "🌐 Browser",
            "📑 PDF",
        ]

        for i, text in enumerate(actions):
            button = QPushButton(text)
            layout.addWidget(button, i // 2, i % 2)