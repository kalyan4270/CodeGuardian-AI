from groq import Groq
import os
from dotenv import load_dotenv
from graph.neo4j_client import neo4j_client
from graph.graph_builder import (
    build_knowledge_graph,
    extract_changed_files
)

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def impact_agent(state: dict) -> dict:
    """
    Phase 3 agent — Neo4j powered impact analysis.

    Steps:
    1. Build/update knowledge graph from PR diff
    2. Query Neo4j for downstream dependencies
    3. Get PR history for changed files
    4. Use LLM to generate impact summary
    """

    repo_name  = state["repo_name"]
    pr_number  = state["pr_number"]
    pr_title   = state["pr_title"]
    pr_diff    = state["pr_diff"]

    # Step 1: Build knowledge graph
    graph_result = build_knowledge_graph(
        repo_name=repo_name,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_diff=pr_diff,
        pr_summary=state.get("code_analysis", "")[:300]
    )

    changed_files = graph_result["changed_files"]

    # Step 2: Query downstream impact
    impact_map = neo4j_client.get_downstream_impact(
        repo_name=repo_name,
        changed_files=changed_files
    )

    # Step 3: Get PR history for changed files
    history_context = []
    for file_path in changed_files[:3]:  # limit to 3 files
        history = neo4j_client.get_pr_history(
            repo_name=repo_name,
            file_path=file_path,
            limit=3
        )
        if history:
            history_context.append({
                "file": file_path,
                "recent_prs": history
            })

    # Step 4: Get hotspot files
    hotspots = neo4j_client.get_most_changed_files(
        repo_name=repo_name,
        limit=5
    )

    # Step 5: LLM generates impact analysis summary
    impact_prompt = f"""
    You are analyzing the downstream impact of a pull request.

    PR Title: {pr_title}
    Changed Files: {changed_files}

    Dependency Impact Map (files that depend on changed files):
    {impact_map if impact_map else "No downstream dependencies found yet."}

    Recent PR History for Changed Files:
    {history_context if history_context else "First time these files are being reviewed."}

    Frequently Changed Files (hotspots):
    {hotspots if hotspots else "Not enough history yet."}

    Provide impact analysis covering:
    1. Which services or modules are affected by this change
    2. Risk level: LOW / MEDIUM / HIGH based on dependencies
    3. Files that need regression testing
    4. Any concerning patterns (e.g. hotspot file changed again)
    5. Recommended review priority

    Be specific and concise.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": impact_prompt}],
        max_tokens=1024,
        temperature=0.3
    )

    state["impact_analysis"] = response.choices[0].message.content
    state["graph_metadata"] = {
        "changed_files":       changed_files,
        "dependencies_mapped": graph_result["dependencies_mapped"],
        "impacted_files":      impact_map,
        "hotspot_files":       hotspots,
        "graph_message":       graph_result["message"]
    }

    return state