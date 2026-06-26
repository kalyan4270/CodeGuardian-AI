def format_report(report: dict) -> dict:
    """
    Formats the final report for API response.
    In Phase 5 this will also generate voice summary.
    """
    return {
        "pr_number": report.get("pr_number"),
        "repo": report.get("repo"),
        "pr_title": report.get("pr_title"),
        "status": report.get("status"),
        "review": {
            "code_analysis": report.get("summary", {}).get("code_analysis", ""),
            "security_findings": "...",
            "style_issues": "...",
            "impact_analysis": "...",
            "voice_summary": "..."
        }
    }