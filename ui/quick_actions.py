from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QPushButton,
)

from ui.theme import COLORS


class QuickActionsWidget(QFrame):

    actionTriggered = Signal(str)

    def __init__(self):
        super().__init__()

        self.setObjectName("quickCard")

        self.setStyleSheet(f"""
        QFrame#quickCard {{
            background:{COLORS["surface"]};
            border-radius:14px;
        }}

        QPushButton {{
            background:{COLORS["surface_light"]};
            border:1px solid {COLORS["border"]};
            border-radius:14px;
            padding:16px;
            min-height:52px;
            font-size:11pt;
            font-weight:600;
            text-align:center;
        }}

        QPushButton:hover {{
            background:{COLORS["primary_hover"]};
        }}

        QPushButton:pressed {{
            background:{COLORS["primary"]};
        }}
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(12)

        actions = [
            ("📄\nExplain Project", "explain this project"),
            ("👥\nOpen Teams", "open teams"),
            ("📧\nDraft Email", "draft email"),
            ("📁\nSearch Files", "find file"),
            ("🌐\nBrowser", "open browser"),
            ("📑\nSummarize PDF", "summarize pdf"),
        ]

        for index, (label, command) in enumerate(actions):

            button = QPushButton(label)

            button.clicked.connect(
                lambda checked=False, cmd=command:
                self.actionTriggered.emit(cmd)
            )

            layout.addWidget(
                button,
                index // 2,
                index % 2,
            )