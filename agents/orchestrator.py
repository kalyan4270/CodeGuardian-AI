from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from langgraph.graph import END, StateGraph

from agents.code_agent import code_analysis_agent
from agents.impact_agent import impact_agent
from agents.security_agent import security_agent
from agents.style_agent import style_agent
from core.llm import complete
from models.state import ReviewState

_AGENT_RUNNERS = (
    code_analysis_agent,
    security_agent,
    style_agent,
    impact_agent,
)


def _merge_agent_results(base: ReviewState, results: list[ReviewState]) -> ReviewState:
    merged = dict(base)
    for result in results:
        merged.update(result)
    return merged  # type: ignore[return-value]


def parallel_agents(state: ReviewState) -> ReviewState:
    """Run all review agents concurrently and merge their outputs."""
    with ThreadPoolExecutor(max_workers=len(_AGENT_RUNNERS)) as executor:
        futures = {
            executor.submit(runner, dict(state)): runner.__name__
            for runner in _AGENT_RUNNERS
        }
        results = [future.result() for future in as_completed(futures)]

    return _merge_agent_results(state, results)


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
        "pr_number": state["pr_number"],
        "repo": state["repo_name"],
        "pr_title": state["pr_title"],
        "executive_summary": complete(summary_prompt, max_tokens=256, temperature=0.3),
        "summary": {
            "code_analysis": state["code_analysis"],
            "security_findings": state["security_findings"],
            "style_issues": state["style_issues"],
            "impact_analysis": state["impact_analysis"],
        },
        "graph_metadata": state.get("graph_metadata", {}),
        "status": "completed",
        "agents_run": ["code_analysis", "security", "style", "impact"],
        "phase": 4,
    }
    return state


def build_review_graph():
    workflow = StateGraph(ReviewState)
    workflow.add_node("parallel_agents", parallel_agents)
    workflow.add_node("report_generator", report_generator_agent)
    workflow.set_entry_point("parallel_agents")
    workflow.add_edge("parallel_agents", "report_generator")
    workflow.add_edge("report_generator", END)
    return workflow.compile()


review_graph = build_review_graph()
