from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langgraph.graph import END, StateGraph

from agents.code_agent import code_analysis_agent
from agents.impact_agent import impact_agent
from agents.security_agent import security_agent
from agents.style_agent import style_agent
from core.llm import complete
from core.logging import get_logger
from models.state import ReviewState

logger = get_logger(__name__)

_AGENT_RUNNERS = (
    code_analysis_agent,
    security_agent,
    style_agent,
    impact_agent,
)

_AGENT_OUTPUT_KEYS: dict[str, str | tuple[str, ...]] = {
    "code_analysis_agent": "code_analysis",
    "security_agent":      "security_findings",
    "style_agent":         "style_issues",
    "impact_agent":        ("impact_analysis", "graph_metadata"),
}


def _merge_agent_results(
    base: ReviewState,
    results: list[ReviewState],
    completed_agents: list[str],
) -> ReviewState:
    """
    Merge only the specific keys each agent owns.
    Prevents agents overwriting each other with empty strings.
    """
    merged = dict(base)

    for agent_name, result in zip(completed_agents, results):
        keys = _AGENT_OUTPUT_KEYS.get(agent_name, [])
        if isinstance(keys, str):
            keys = (keys,)
        for key in keys:
            value = result.get(key)
            if value:
                merged[key] = value

    return merged  # type: ignore[return-value]


def parallel_agents(state: ReviewState) -> ReviewState:
    """Run all review agents concurrently and merge their outputs."""
    with ThreadPoolExecutor(max_workers=len(_AGENT_RUNNERS)) as executor:
        futures = {}
        for i, runner in enumerate(_AGENT_RUNNERS):
            if i > 0:
                time.sleep(0.5)
            future = executor.submit(runner, dict(state))
            futures[future] = runner.__name__

        results = []
        completed_agents = []

        for future in as_completed(futures):
            agent_name = futures[future]
            try:
                result = future.result()
                logger.info("✅ %s completed", agent_name)
                results.append(result)
                completed_agents.append(agent_name)
            except Exception as exc:
                logger.error("❌ %s failed: %s", agent_name, exc)

    return _merge_agent_results(state, results, completed_agents)


def report_generator_agent(state: ReviewState) -> ReviewState:
    summary_prompt = f"""
Based on the following code review findings, write a 2-3 sentence
executive summary of this pull request review:

Code Analysis: {state['code_analysis'][:400]}
Security: {state['security_findings'][:300]}
Style: {state['style_issues'][:300]}
Impact: {state['impact_analysis'][:300]}

Mention the most critical issues and overall risk level.
"""
    state["final_report"] = {
        "pr_number":         state["pr_number"],
        "repo":              state["repo_name"],
        "pr_title":          state["pr_title"],
        "executive_summary": complete(
            summary_prompt, max_tokens=256, temperature=0.3
        ),
        "summary": {
            "code_analysis":     state["code_analysis"],
            "security_findings": state["security_findings"],
            "style_issues":      state["style_issues"],
            "impact_analysis":   state["impact_analysis"],
        },
        "graph_metadata": state.get("graph_metadata", {}),
        "status":         "completed",
        "agents_run":     ["code_analysis", "security", "style", "impact"],
        "phase":          4,
    }
    return state


def build_review_graph() -> Any:
    workflow = StateGraph(ReviewState)
    workflow.add_node("parallel_agents",    parallel_agents)
    workflow.add_node("report_generator",   report_generator_agent)
    workflow.set_entry_point("parallel_agents")
    workflow.add_edge("parallel_agents",    "report_generator")
    workflow.add_edge("report_generator",   END)
    return workflow.compile()


review_graph = build_review_graph()