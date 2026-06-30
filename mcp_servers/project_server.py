"""FastMCP project analysis server."""

from __future__ import annotations

import logging
from typing import Any

from services.project_scanner import scan_project

logger = logging.getLogger(__name__)


def _serialize_error(message: str) -> dict[str, Any]:
    """Return a consistent error payload for MCP tool responses."""
    return {"success": False, "error": message}


def scan_project_impl(path: str = ".") -> dict[str, Any]:
    """
    Scan a project directory and return structured metadata.
    
    Args:
        path: Path to the project directory (defaults to current directory)
        
    Returns:
        Dictionary containing project metadata
    """
    project_path = path.strip() if path else "."
    
    try:
        result = scan_project(project_path)
        return result
    except Exception as exc:
        logger.exception("Project scan failed for path: %s", project_path)
        return _serialize_error(f"Failed to scan project: {exc}")
