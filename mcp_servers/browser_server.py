"""FastMCP browser server for browser automation."""

import logging
import subprocess
from typing import Any

from fastmcp import FastMCP

from config.settings import DEFAULT_BROWSER

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
            [
                "open",
                "-a",
                DEFAULT_BROWSER,
                target,
            ],
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

def google_search_impl(query: str) -> dict[str, Any]:
    """
    Search Google for a query.
    """

    if not query.strip():
        return _serialize_error("Search query is required")

    target = (
        "https://www.google.com/search?q="
        + query.strip().replace(" ", "+")
    )

    try:
        subprocess.run(
            [
                "open",
                "-a",
                DEFAULT_BROWSER,
                target,
            ],
            check=True,
        )


        return {
            "success": True,
            "message": f"Searched Google for '{query}'",
            "url": target,
        }

    except Exception as exc:
        logger.exception("Unable to search Google")
        return _serialize_error(str(exc))


@mcp.tool()
def google_search(query: str) -> dict[str, Any]:
    """
    Search Google.
    """
    return google_search_impl(query)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run()