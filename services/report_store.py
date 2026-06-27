"""In-memory report cache for voice and query endpoints."""

from __future__ import annotations

import threading
from typing import Any


def build_report_key(repo: str, pr_number: int) -> str:
    """Canonical key: owner/repo:42."""
    return f"{repo}:{pr_number}"


class ReportStore:
    """Thread-safe store for completed review reports."""

    def __init__(self) -> None:
        self._reports: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def save(self, repo: str, pr_number: int, report: dict[str, Any]) -> str:
        key = build_report_key(repo, pr_number)
        with self._lock:
            self._reports[key] = report
        return key

    def get(self, repo: str, pr_number: int) -> dict[str, Any] | None:
        key = build_report_key(repo, pr_number)
        with self._lock:
            return self._reports.get(key)

    def get_by_path(self, repo_owner: str, repo_name: str, pr_number: int) -> dict[str, Any] | None:
        return self.get(f"{repo_owner}/{repo_name}", pr_number)


report_store = ReportStore()
