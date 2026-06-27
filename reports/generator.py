def format_report(report: dict) -> dict:
    """
    Formats final report for API response.
    """
    return {
        "pr_number":         report.get("pr_number"),
        "repo":              report.get("repo"),
        "pr_title":          report.get("pr_title"),
        "status":            report.get("status"),
        "phase":             report.get("phase"),
        "agents_run":        report.get("agents_run", []),
        "executive_summary": report.get("executive_summary", ""),
        "review": {
            "code_analysis":     report.get("summary", {}).get("code_analysis", ""),
            "security_findings": report.get("summary", {}).get("security_findings", ""),
            "style_issues":      report.get("summary", {}).get("style_issues", ""),
            "impact_analysis":   report.get("summary", {}).get("impact_analysis", ""),
            "voice_summary":     "..."
        }
    }