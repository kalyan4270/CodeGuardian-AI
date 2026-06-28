"""LangGraph pipeline state definition."""

from __future__ import annotations

from typing import Any, TypedDict


class ReviewState(TypedDict):
    pr_diff: str
    pr_description: str
    pr_title: str
    repo_name: str
    pr_number: int
    code_analysis: str
    security_findings: str
    style_issues: str
    impact_analysis: str
    graph_metadata: dict[str, Any]
    final_report: dict[str, Any]
