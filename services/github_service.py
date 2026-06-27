"""GitHub API integration for pull request data."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx

from core.config import get_settings
from core.exceptions import GitHubAPIError
from core.logging import get_logger

logger = get_logger(__name__)


def extract_repo_name(repo_url: str) -> str:
    """Extract owner/repo from a GitHub repository URL."""
    path = urlparse(str(repo_url).rstrip("/")).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
    return f"{parts[-2]}/{parts[-1]}"


async def fetch_pr_data(repo_url: str, pr_number: int) -> dict[str, Any]:
    """Fetch PR metadata and unified diff from the GitHub REST API."""
    settings = get_settings()
    repo_name = extract_repo_name(repo_url)
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    pr_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        logger.info("Fetching PR #%s from %s", pr_number, repo_name)
        pr_response = await client.get(pr_url, headers=headers)
        if pr_response.is_error:
            raise GitHubAPIError(pr_response.status_code, pr_response.text)

        pr_data = pr_response.json()
        diff_headers = {**headers, "Accept": "application/vnd.github.v3.diff"}
        diff_response = await client.get(pr_url, headers=diff_headers)
        if diff_response.is_error:
            raise GitHubAPIError(diff_response.status_code, diff_response.text)

    return {
        "pr_description": pr_data.get("body") or "No description provided",
        "pr_title": pr_data.get("title", ""),
        "pr_diff": diff_response.text[: settings.max_diff_chars],
        "repo_name": repo_name,
        "pr_number": pr_number,
    }
