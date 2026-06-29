"""FastMCP browser server for browser automation."""

import logging
import subprocess
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("desktop-browser")


def _serialize_error(message: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": message,
    }


def open_browser_impl(url: str) -> dict[str, Any]:
    """
    Open a webpage using Playwright.
    """

    if not url.strip():
        return _serialize_error("URL is required")

    target = url.strip()

    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target

    try:
        subprocess.run(
            ["open", target],
            check=True,
        )

        return {
            "success": True,
            "message": f"Opened {target}",
            "url": target,
        }

    except Exception as exc:
        logger.exception("Unable to open browser")
        return _serialize_error(str(exc))
       
@mcp.tool()
def open_browser(url: str) -> dict[str, Any]:
    """
    Open a webpage in the browser.
    """
    return open_browser_impl(url)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run()