from __future__ import annotations

from agents.base import run_review_agent
from models.state import ReviewState

_STYLE_INSTRUCTIONS = """
Review strictly for style and standards:
1. Naming conventions (variables, functions, classes)
2. Missing or poor documentation/docstrings
3. Code readability and clarity
4. DRY violations (repeated code)
5. Function or class complexity (too long, too many responsibilities)
6. Proper error handling patterns

For each issue:
- Type: Naming / Documentation / Readability / DRY / Complexity / ErrorHandling
- Location: file/line reference
- Issue: what's wrong
- Suggestion: how to improve

Also mention what's done well.
Be constructive and specific.
"""


def style_agent(state: ReviewState) -> ReviewState:
    state["style_issues"] = run_review_agent(
        state,
        system_role="You are a senior software engineer reviewing code style and standards.",
        instructions=_STYLE_INSTRUCTIONS,
        temperature=0.3,
    )
    return state
