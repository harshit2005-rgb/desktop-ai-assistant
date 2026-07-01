"""FastMCP GitHub server for repository and commit inspection."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

from services.github_controller import GitHubController

logger = logging.getLogger(__name__)

mcp = FastMCP("github")
controller = GitHubController()


def _serialize_error(message: str) -> dict[str, Any]:
    """Return a consistent error payload for MCP tool responses."""
    return {"success": False, "error": message}


def list_repositories_impl() -> dict[str, Any]:
    """List repositories visible to the configured GitHub account."""
    return controller.list_repositories()


def list_branches_impl(repo: str) -> dict[str, Any]:
    """List branches for a repository."""
    return controller.list_branches(repo)


def list_recent_commits_impl(repo: str, limit: int = 5) -> dict[str, Any]:
    """List recent commits for a repository."""
    return controller.list_recent_commits(repo, limit=limit)


def get_commit_impl(repo: str, sha: str) -> dict[str, Any]:
    """Get a specific commit by SHA or ref."""
    return controller.get_commit(repo, sha)


def get_repository_impl(repo: str) -> dict[str, Any]:
    """Get repository metadata."""
    return controller.get_repository(repo)


@mcp.tool()
def list_repositories() -> dict[str, Any]:
    """List GitHub repositories for the configured account."""
    return list_repositories_impl()


@mcp.tool()
def list_branches(repo: str) -> dict[str, Any]:
    """List branches for the provided repository."""
    return list_branches_impl(repo)


@mcp.tool()
def list_recent_commits(repo: str, limit: int = 5) -> dict[str, Any]:
    """List recent commits for the provided repository."""
    return list_recent_commits_impl(repo, limit=limit)


@mcp.tool()
def get_commit(repo: str, sha: str) -> dict[str, Any]:
    """Get a commit by repository and SHA/ref."""
    return get_commit_impl(repo, sha)


@mcp.tool()
def get_repository(repo: str) -> dict[str, Any]:
    """Get repository details for the provided repository."""
    return get_repository_impl(repo)
