"""Application entrypoint for the Desktop MCP Assistant."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from ui.sidekick_window import SidekickWindow


def configure_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> int:
    """Start the PySide6 desktop application."""
    configure_logging()
    app = QApplication(sys.argv)
    window = SidekickWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
