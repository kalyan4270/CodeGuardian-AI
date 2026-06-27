from __future__ import annotations

from typing import Any


def format_report(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary", {})
    return {
        "pr_number": report.get("pr_number"),
        "repo": report.get("repo"),
        "pr_title": report.get("pr_title"),
        "status": report.get("status"),
        "phase": report.get("phase"),
        "agents_run": report.get("agents_run", []),
        "executive_summary": report.get("executive_summary", ""),
        "review": {
            "code_analysis": summary.get("code_analysis", ""),
            "security_findings": summary.get("security_findings", ""),
            "style_issues": summary.get("style_issues", ""),
            "impact_analysis": summary.get("impact_analysis", ""),
        },
        "graph_metadata": report.get("graph_metadata", {}),
    }
