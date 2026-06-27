"""Shared utilities for review agents."""

from __future__ import annotations

from core.llm import complete
from models.state import ReviewState


def build_pr_context(state: ReviewState) -> str:
    return (
        f"PR Title: {state['pr_title']}\n"
        f"PR Description: {state['pr_description']}\n\n"
        f"Code Changes:\n{state['pr_diff']}"
    )


def run_review_agent(
    state: ReviewState,
    *,
    system_role: str,
    instructions: str,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    prompt = f"{system_role}\n\n{build_pr_context(state)}\n\n{instructions}"
    return complete(prompt, temperature=temperature, max_tokens=max_tokens)
