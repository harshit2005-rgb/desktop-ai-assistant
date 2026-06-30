"""Cross-platform Microsoft Teams controller."""

import platform
import subprocess
from typing import Any


class TeamsController:
    """Controls the Microsoft Teams desktop application."""

    def open(self) -> dict[str, Any]:
        """Open Microsoft Teams."""

        system = platform.system()

        if system == "Darwin":
            return self._open_mac()

        if system == "Windows":
            return self._open_windows()

        return {
            "success": False,
            "error": f"Unsupported platform: {system}",
        }

    def open_calendar(self) -> dict[str, Any]:
        """Open Teams Calendar."""
        pass

    def open_chat(self) -> dict[str, Any]:
        """Open Teams Chat."""
        pass

    # -----------------------
    # macOS
    # -----------------------

    def _open_mac(self) -> dict[str, Any]:
        try:
            subprocess.run(
                [
                    "open",
                    "-a",
                    "Microsoft Teams",
                ],
                check=True,
            )

            return {
                "success": True,
                "message": "Opened Microsoft Teams",
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

    # -----------------------
    # Windows
    # -----------------------

    def _open_windows(self) -> dict[str, Any]:
        try:
            subprocess.run(
                [
                    "cmd",
                    "/c",
                    "start",
                    "msteams:",
                ],
                check=True,
            )

            return {
                "success": True,
                "message": "Opened Microsoft Teams",
            }

        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }