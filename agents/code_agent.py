from __future__ import annotations

from agents.base import run_review_agent
from models.state import ReviewState

_CODE_INSTRUCTIONS = """
Provide a structured review covering:
1. Potential bugs or logic errors
2. Code quality issues
3. Performance concerns
4. Positive aspects of the change

Be specific and actionable.
"""


def code_analysis_agent(state: ReviewState) -> ReviewState:
    state["code_analysis"] = run_review_agent(
        state,
        system_role="You are an expert code reviewer analyzing a pull request.",
        instructions=_CODE_INSTRUCTIONS,
        temperature=0.3,
    )
    return state
