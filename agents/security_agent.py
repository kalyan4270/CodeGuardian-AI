from __future__ import annotations

from agents.base import run_review_agent
from models.state import ReviewState

_SECURITY_INSTRUCTIONS = """
Analyze strictly for security issues:
1. Hardcoded secrets, API keys, passwords, tokens
2. SQL injection or command injection vulnerabilities
3. Unsafe input handling or missing validation
4. Authentication or authorization issues
5. Sensitive data exposure

For each issue found:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Location: which file/line
- Description: what the issue is
- Fix: how to resolve it

If no issues found, explicitly state "No security issues detected."
Be concise and specific.
"""


def security_agent(state: ReviewState) -> ReviewState:
    state["security_findings"] = run_review_agent(
        state,
        system_role="You are a security expert reviewing a pull request for vulnerabilities.",
        instructions=_SECURITY_INSTRUCTIONS,
        temperature=0.1,
    )
    return state
