"""FastMCP application server for local desktop application operations."""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("desktop-applications")

APP_ALIASES = {
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "vscode": "Visual Studio Code",
    "vs code": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "spotify": "Spotify",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "iterm2": "iTerm",
    "safari": "Safari",
    "finder": "Finder",
}


def _serialize_error(message: str) -> dict[str, Any]:
    """Return a consistent error payload for MCP tool responses."""
    return {"success": False, "error": message}


def normalize_app_name(app_name: str) -> str:
    """Map common app nicknames to their macOS application names."""
    cleaned = app_name.strip()
    return APP_ALIASES.get(cleaned.lower(), cleaned)


def open_application_impl(app_name: str) -> dict[str, Any]:
    """Open an application by name. macOS is supported initially."""
    normalized = normalize_app_name(app_name)
    if not normalized:
        return _serialize_error("app_name is required")

    if os.name != "posix" or os.uname().sysname != "Darwin":
        return _serialize_error("open_application currently supports macOS only")

    try:
        completed = subprocess.run(
            ["open", "-a", normalized],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # noqa: BLE001 - launch failures vary by OS.
        logger.exception("Unable to open application %s", normalized)
        return _serialize_error(str(exc))

    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or "Unknown error"
        return _serialize_error(f"Failed to open {normalized}: {error}")

    return {
        "success": True,
        "message": f"Opened {normalized}",
        "application": normalized,
    }


def list_running_applications_impl() -> dict[str, Any]:
    """Return currently running GUI application names on macOS."""
    if os.name != "posix" or os.uname().sysname != "Darwin":
        return _serialize_error("list_running_applications currently supports macOS only")

    script = (
        'tell application "System Events" to get the name of every process '
        "whose background only is false"
    )
    try:
        completed = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # noqa: BLE001 - osascript failures vary by host.
        logger.exception("Unable to list running applications")
        return _serialize_error(str(exc))

    if completed.returncode != 0:
        error = completed.stderr.strip() or completed.stdout.strip() or "Unknown error"
        return _serialize_error(f"Failed to list applications: {error}")

    apps = [item.strip() for item in completed.stdout.split(",") if item.strip()]
    apps.sort(key=str.lower)
    return {"success": True, "count": len(apps), "applications": apps}


@mcp.tool()
def open_application(app_name: str) -> dict[str, Any]:
    """Open applications such as Chrome, VS Code, Spotify, and Terminal."""
    return open_application_impl(app_name)


@mcp.tool()
def list_running_applications() -> dict[str, Any]:
    """Return currently running GUI applications."""
    return list_running_applications_impl()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run()
