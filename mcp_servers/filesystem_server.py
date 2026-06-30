"""FastMCP filesystem server for local desktop file operations."""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP("desktop-filesystem")

SEARCH_ROOTS = (
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
)
COMMON_FOLDERS = {root.name.lower(): root for root in SEARCH_ROOTS}


def _serialize_error(message: str) -> dict[str, Any]:
    """Return a consistent error payload for MCP tool responses."""
    return {"success": False, "error": message}


def find_file_impl(filename: str) -> dict[str, Any]:
    """Search common user folders recursively for files matching a name fragment."""
    query = filename.strip()
    if not query:
        return _serialize_error("filename is required")

    matches: list[str] = []
    query_lower = query.lower()

    for root in SEARCH_ROOTS:
        if not root.exists():
            logger.debug("Skipping missing search root: %s", root)
            continue

        try:
            for path in root.rglob("*"):
                try:
                    if query_lower in path.name.lower():
                        matches.append(str(path))
                except OSError as exc:
                    logger.debug("Skipping unreadable path %s: %s", path, exc)
        except OSError as exc:
            logger.warning("Unable to search %s: %s", root, exc)

    matches.sort()
    return {"success": True, "message": f"Found {len(matches)} matching file(s) for '{query}'.", "query": query, "count": len(matches), "matches": matches}


def list_directory_impl(path: str) -> dict[str, Any]:
    """Return files and folders in a directory."""
    directory = COMMON_FOLDERS.get(path.strip().lower(), Path(path).expanduser())
    if not directory.exists():
        return _serialize_error(f"Directory does not exist: {directory}")
    if not directory.is_dir():
        return _serialize_error(f"Path is not a directory: {directory}")

    entries: list[dict[str, Any]] = []
    try:
        for child in sorted(directory.iterdir(), key=lambda item: item.name.lower()):
            entries.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "type": "directory" if child.is_dir() else "file",
                }
            )
    except OSError as exc:
        logger.exception("Unable to list directory %s", directory)
        return _serialize_error(str(exc))

    return {"success": True, "path": str(directory), "entries": entries}


def open_file_impl(path: str) -> dict[str, Any]:
    """Open a local file or folder with the operating system default application."""
    target = Path(path).expanduser()
    if not target.exists():
        return _serialize_error(f"Path does not exist: {target}")

    try:
        if os.name == "posix":
            opener = "open" if os.uname().sysname == "Darwin" else "xdg-open"
            subprocess.Popen([opener, str(target)])
        elif os.name == "nt":
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            return _serialize_error(f"Unsupported operating system: {os.name}")
    except Exception as exc:  # noqa: BLE001 - desktop launch failures vary by OS.
        logger.exception("Unable to open file %s", target)
        return _serialize_error(str(exc))

    return {"success": True, "message": f"Opened {target}", "path": str(target)}


def get_file_info_impl(path: str) -> dict[str, Any]:
    """Return basic metadata for a local file or folder."""
    target = Path(path).expanduser()
    if not target.exists():
        return _serialize_error(f"Path does not exist: {target}")

    try:
        stat = target.stat()
    except OSError as exc:
        logger.exception("Unable to stat path %s", target)
        return _serialize_error(str(exc))

    return {
        "success": True,
        "message": f"Retrieved information for {target.name}.",
        "name": target.name,
        "path": str(target),
        "type": "directory" if target.is_dir() else "file",
        "size_bytes": stat.st_size,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(timespec="seconds"),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


@mcp.tool()
def find_file(filename: str) -> dict[str, Any]:
    """Search Desktop, Documents, and Downloads recursively for matching file paths."""
    return find_file_impl(filename)


@mcp.tool()
def list_directory(path: str) -> dict[str, Any]:
    """Return files and folders in a directory."""
    return list_directory_impl(path)


@mcp.tool()
def open_file(path: str) -> dict[str, Any]:
    """Open the file using the operating system default application."""
    return open_file_impl(path)


@mcp.tool()
def get_file_info(path: str) -> dict[str, Any]:
    """Return file name, size, created date, and modified date."""
    return get_file_info_impl(path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run()
