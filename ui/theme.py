"""Theme configuration for Sidekick AI."""

WINDOW_WIDTH = 430
WINDOW_HEIGHT = 720

COLORS = {
    "background": "#181818",
    "surface": "#242424",
    "surface_light": "#2E2E2E",

    "primary": "#00C2FF",
    "primary_hover": "#009FCC",

    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",

    "text": "#FFFFFF",
    "text_secondary": "#B3B3B3",

    "border": "#3A3A3A",

    "input": "#303030",
}

FONT = {
    "title": 18,
    "subtitle": 12,
    "body": 11,
    "small": 10,
}

RADIUS = 12

PADDING = 12

def app_stylesheet() -> str:
    return f"""
    QMainWindow {{
        background-color: {COLORS["background"]};
        color: {COLORS["text"]};
    }}

    QWidget {{
        background-color: {COLORS["background"]};
        color: {COLORS["text"]};
        font-size: 11pt;
    }}

    QTextEdit {{
        background-color: {COLORS["surface"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS}px;
        padding: 8px;
    }}

    QLineEdit {{
        background-color: {COLORS["input"]};
        border: 1px solid {COLORS["border"]};
        border-radius: {RADIUS}px;
        padding: 10px;
    }}

    QPushButton {{
        background-color: {COLORS["primary"]};
        color: white;
        border: none;
        border-radius: {RADIUS}px;
        padding: 8px;
    }}

    QPushButton:hover {{
        background-color: {COLORS["primary_hover"]};
    }}

    QGroupBox {{
        border: none;
        font-weight: bold;
        margin-top: 10px;
    }}
    """