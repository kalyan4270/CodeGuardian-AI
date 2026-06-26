import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def extract_repo_name(repo_url: str) -> str:
    """Extract 'owner/repo' from GitHub URL."""
    # handles https://github.com/owner/repo
    parts = repo_url.rstrip("/").split("/")
    return f"{parts[-2]}/{parts[-1]}"

async def fetch_pr_data(repo_url: str, pr_number: int) -> dict:
    """
    Fetches PR title, description, and code diff from GitHub API.
    Returns dict with pr_description and pr_diff.
    """
    repo_name = extract_repo_name(repo_url)

    async with httpx.AsyncClient() as client:

        # Fetch PR metadata
        pr_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_number}"
        pr_response = await client.get(pr_url, headers=HEADERS)
        pr_response.raise_for_status()
        pr_data = pr_response.json()

        # Fetch PR diff
        diff_headers = {**HEADERS, "Accept": "application/vnd.github.v3.diff"}
        diff_response = await client.get(pr_url, headers=diff_headers)
        diff_response.raise_for_status()

        return {
            "pr_description": pr_data.get("body", "No description provided"),
            "pr_title": pr_data.get("title", ""),
            "pr_diff": diff_response.text[:6000],  # limit diff size for free tier
            "repo_name": repo_name,
            "pr_number": pr_number
        }