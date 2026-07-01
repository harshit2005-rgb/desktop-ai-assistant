"""GitHub controller for repository and commit inspection via the GitHub REST API."""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

GITHUB_API_BASE = "https://api.github.com"


class GitHubController:
    """Small controller for GitHub repository metadata and commit history."""

    def __init__(self) -> None:
        self.token = os.getenv("GITHUB_TOKEN", "").strip()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _request(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Perform a GitHub REST API request and return parsed JSON."""
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is not configured. Set it in your .env file.")

        response = self.session.get(f"{GITHUB_API_BASE}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def list_repositories(self) -> dict[str, Any]:
        """List repositories visible to the configured GitHub account."""
        try:
            repos = self._request("/user/repos", params={"per_page": 100, "sort": "updated"})
        except Exception as exc:  # noqa: BLE001 - preserve user-friendly tool errors.
            logger.exception("Unable to list GitHub repositories")
            return {"success": False, "error": str(exc)}

        payload = [
            {
                "name": repo.get("full_name"),
                "description": repo.get("description") or "",
                "private": repo.get("private", False),
                "default_branch": repo.get("default_branch"),
                "html_url": repo.get("html_url"),
            }
            for repo in repos
        ]
        return {"success": True, "repositories": payload}

    def list_branches(self, repo: str) -> dict[str, Any]:
        """List branches for a repository."""
        if not repo.strip():
            return {"success": False, "error": "repo is required"}

        try:
            branches = self._request(f"/repos/{repo}/branches", params={"per_page": 100})
        except Exception as exc:  # noqa: BLE001 - preserve user-friendly tool errors.
            logger.exception("Unable to list GitHub branches")
            return {"success": False, "error": str(exc)}

        payload = [
            {
                "name": branch.get("name"),
                "commit_sha": branch.get("commit", {}).get("sha"),
            }
            for branch in branches
        ]
        return {"success": True, "repo": repo, "branches": payload}

    def list_recent_commits(self, repo: str, limit: int = 5) -> dict[str, Any]:
        """List recent commits for a repository."""
        if not repo.strip():
            return {"success": False, "error": "repo is required"}

        safe_limit = max(1, min(int(limit or 5), 30))
        try:
            commits = self._request(
                f"/repos/{repo}/commits",
                params={"per_page": safe_limit, "page": 1},
            )
        except Exception as exc:  # noqa: BLE001 - preserve user-friendly tool errors.
            logger.exception("Unable to list recent GitHub commits")
            return {"success": False, "error": str(exc)}

        payload = [
            {
                "sha": commit.get("sha"),
                "message": commit.get("commit", {}).get("message"),
                "author": commit.get("commit", {}).get("author", {}).get("name"),
                "date": commit.get("commit", {}).get("author", {}).get("date"),
                "html_url": commit.get("html_url"),
            }
            for commit in commits
        ]
        return {"success": True, "repo": repo, "commits": payload}

    def get_commit(self, repo: str, sha: str) -> dict[str, Any]:
        """Fetch one commit by SHA or ref."""
        if not repo.strip():
            return {"success": False, "error": "repo is required"}
        if not sha.strip():
            return {"success": False, "error": "sha is required"}

        try:
            commit = self._request(f"/repos/{repo}/commits/{sha}")
        except Exception as exc:  # noqa: BLE001 - preserve user-friendly tool errors.
            logger.exception("Unable to get GitHub commit")
            return {"success": False, "error": str(exc)}

        return {
            "success": True,
            "repo": repo,
            "sha": commit.get("sha"),
            "message": commit.get("commit", {}).get("message"),
            "author": commit.get("commit", {}).get("author", {}).get("name"),
            "date": commit.get("commit", {}).get("author", {}).get("date"),
            "html_url": commit.get("html_url"),
            "files": [
                {
                    "filename": change.get("filename"),
                    "status": change.get("status"),
                    "additions": change.get("additions"),
                    "deletions": change.get("deletions"),
                }
                for change in commit.get("files", []) or []
            ],
        }

    def get_repository(self, repo: str) -> dict[str, Any]:
        """Fetch repository metadata."""
        if not repo.strip():
            return {"success": False, "error": "repo is required"}

        try:
            repository = self._request(f"/repos/{repo}")
        except Exception as exc:  # noqa: BLE001 - preserve user-friendly tool errors.
            logger.exception("Unable to get GitHub repository")
            return {"success": False, "error": str(exc)}

        return {
            "success": True,
            "repo": repo,
            "name": repository.get("full_name"),
            "description": repository.get("description") or "",
            "private": repository.get("private", False),
            "default_branch": repository.get("default_branch"),
            "language": repository.get("language"),
            "html_url": repository.get("html_url"),
            "stars": repository.get("stargazers_count"),
            "forks": repository.get("forks_count"),
            "open_issues": repository.get("open_issues_count"),
        }
