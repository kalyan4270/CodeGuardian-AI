from __future__ import annotations

from core.llm import complete
from graph.graph_builder import build_knowledge_graph
from graph.neo4j_client import neo4j_client
from models.state import ReviewState

_MAX_HISTORY_FILES = 3
_MAX_HISTORY_PRS = 3
_MAX_HOTSPOTS = 5


def impact_agent(state: ReviewState) -> ReviewState:
    repo_name = state["repo_name"]
    pr_number = state["pr_number"]
    pr_title = state["pr_title"]
    pr_diff = state["pr_diff"]

    graph_result = build_knowledge_graph(
        repo_name=repo_name,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_diff=pr_diff,
        pr_summary=state.get("code_analysis", "")[:300],
    )
    changed_files = graph_result["changed_files"]

    impact_map = neo4j_client.get_downstream_impact(
        repo_name=repo_name,
        changed_files=changed_files,
    )

    history_context: list[dict] = []
    for file_path in changed_files[:_MAX_HISTORY_FILES]:
        history = neo4j_client.get_pr_history(
            repo_name=repo_name,
            file_path=file_path,
            limit=_MAX_HISTORY_PRS,
        )
        if history:
            history_context.append({"file": file_path, "recent_prs": history})

    hotspots = neo4j_client.get_most_changed_files(
        repo_name=repo_name,
        limit=_MAX_HOTSPOTS,
    )

    impact_prompt = f"""
You are analyzing the downstream impact of a pull request.

PR Title: {pr_title}
Changed Files: {changed_files}

Dependency Impact Map (files that depend on changed files):
{impact_map or "No downstream dependencies found yet."}

Recent PR History for Changed Files:
{history_context or "First time these files are being reviewed."}

Frequently Changed Files (hotspots):
{hotspots or "Not enough history yet."}

Provide impact analysis covering:
1. Which services or modules are affected by this change
2. Risk level: LOW / MEDIUM / HIGH based on dependencies
3. Files that need regression testing
4. Any concerning patterns (e.g. hotspot file changed again)
5. Recommended review priority

Be specific and concise.
"""

    state["impact_analysis"] = complete(impact_prompt, temperature=0.3)
    state["graph_metadata"] = {
        "changed_files": changed_files,
        "dependencies_mapped": graph_result["dependencies_mapped"],
        "impacted_files": impact_map,
        "hotspot_files": hotspots,
        "graph_message": graph_result["message"],
    }
    return state
