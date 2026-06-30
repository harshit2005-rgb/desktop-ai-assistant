"""FastMCP Teams server for Microsoft Teams automation."""

import logging
import platform
import subprocess
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("desktop-teams")


def _serialize_error(message: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": message,
    }


def open_teams_web_impl() -> dict[str, Any]:
    """
    Open Microsoft Teams Web.
    """

    url = "https://teams.microsoft.com"

    try:
        if platform.system() == "Darwin":
            subprocess.run(
                ["open", url],
                check=True,
            )
        elif platform.system() == "Windows":
            subprocess.run(
                ["cmd", "/c", "start", url],
                check=True,
            )
        else:
            return _serialize_error("Unsupported operating system")

        return {
            "success": True,
            "message": "Opened Microsoft Teams Web",
            "url": url,
        }

    except Exception as exc:
        logger.exception("Failed to open Teams Web")
        return _serialize_error(str(exc))


def open_teams_impl() -> dict[str, Any]:
    return controller.open()
    """
    Open Microsoft Teams desktop application.
    Falls back to Teams Web if the desktop app isn't available.
    """

    try:
        if platform.system() == "Darwin":
            subprocess.run(
                ["open", "-a", "Microsoft Teams"],
                check=True,
            )

        elif platform.system() == "Windows":
            subprocess.run(
                ["cmd", "/c", "start", "msteams:"],
                check=True,
            )

        else:
            return _serialize_error("Unsupported operating system")

        return {
            "success": True,
            "message": "Opened Microsoft Teams",
        }

    except Exception:
        logger.warning("Desktop Teams not found. Opening Teams Web instead.")
        return open_teams_web_impl()


@mcp.tool()
def open_teams() -> dict[str, Any]:
    """
    Open Microsoft Teams.
    """
    return open_teams_impl()


@mcp.tool()
def open_teams_web() -> dict[str, Any]:
    """
    Open Microsoft Teams Web.
    """
    return open_teams_web_impl()

def open_teams_calendar_impl() -> dict[str, Any]:
    return controller.open_calendar()
    url = "https://teams.microsoft.com/v2/?clientType=pwa#/calendar"

    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", url], check=True)
        elif platform.system() == "Windows":
            subprocess.run(["cmd", "/c", "start", url], check=True)
        else:
            return _serialize_error("Unsupported operating system")

        return {
            "success": True,
            "message": "Opened Teams Calendar",
            "url": url,
        }

    except Exception as exc:
        return _serialize_error(str(exc))
    
@mcp.tool()
def open_teams_calendar() -> dict[str, Any]:
    """
    Open Microsoft Teams Calendar.
    """
    return open_teams_calendar_impl()    

def open_teams_chat_impl() -> dict[str, Any]:
    return controller.open_chat()
    url = "https://teams.microsoft.com/v2/?clientType=pwa#/chat"

    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", url], check=True)
        elif platform.system() == "Windows":
            subprocess.run(["cmd", "/c", "start", url], check=True)
        else:
            return _serialize_error("Unsupported operating system")

        return {
            "success": True,
            "message": "Opened Teams Chat",
            "url": url,
        }

    except Exception as exc:
        return _serialize_error(str(exc))


@mcp.tool()
def open_teams_chat() -> dict[str, Any]:
    """
    Open Microsoft Teams Chat.
    """
    return open_teams_chat_impl()