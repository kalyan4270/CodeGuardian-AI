import os
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from groq import Groq
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

from agents.security_agent import security_agent
from agents.style_agent import style_agent
from agents.impact_agent import impact_agent

# ---- Updated State ----
class ReviewState(TypedDict):
    pr_diff:           str
    pr_description:    str
    pr_title:          str
    repo_name:         str
    pr_number:         int
    code_analysis:     str
    security_findings: str
    style_issues:      str
    impact_analysis:   str
    graph_metadata:    dict
    final_report:      dict

# ---- Code Analysis Agent ----
def code_analysis_agent(state: ReviewState) -> ReviewState:
    prompt = f"""
    You are an expert code reviewer. Analyse the following pull request.

    PR Title: {state['pr_title']}
    PR Description: {state['pr_description']}

    Code Changes (diff):
    {state['pr_diff']}

    Provide a structured review covering:
    1. Potential bugs or logic errors
    2. Code quality issues
    3. Performance concerns
    4. Positive aspects of the change

    Be specific and actionable.
    """
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",  # best model on Groq
        # alternatives if you hit rate limits:
        # model="llama-3.1-8b-instant"      # faster, lighter
        # model="mixtral-8x7b-32768"        # good for code
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.3
    )
    state["code_analysis"] = response.choices[0].message.content
    return state

# ---- Parallel Runner (all 4 agents) ----
def parallel_agents(state: ReviewState) -> ReviewState:
    """
    Runs all 4 agents simultaneously.
    Impact agent runs alongside others — Neo4j
    queries are fast enough for parallel execution.
    """
    with ThreadPoolExecutor(max_workers=4) as executor:
        code_future     = executor.submit(code_analysis_agent, state.copy())
        security_future = executor.submit(security_agent, state.copy())
        style_future    = executor.submit(style_agent, state.copy())
        impact_future   = executor.submit(impact_agent, state.copy())

        code_result     = code_future.result()
        security_result = security_future.result()
        style_result    = style_future.result()
        impact_result   = impact_future.result()

    # Merge all results
    state["code_analysis"]     = code_result["code_analysis"]
    state["security_findings"] = security_result["security_findings"]
    state["style_issues"]      = style_result["style_issues"]
    state["impact_analysis"]   = impact_result["impact_analysis"]
    state["graph_metadata"]    = impact_result.get("graph_metadata", {})

    return state

# ---- Report Generator ----
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
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=256,
        temperature=0.3
    )

    state["final_report"] = {
        "pr_number":         state["pr_number"],
        "repo":              state["repo_name"],
        "pr_title":          state["pr_title"],
        "executive_summary": response.choices[0].message.content,
        "summary": {
            "code_analysis":     state["code_analysis"],
            "security_findings": state["security_findings"],
            "style_issues":      state["style_issues"],
            "impact_analysis":   state["impact_analysis"],
        },
        "graph_metadata": state.get("graph_metadata", {}),
        "status":         "completed",
        "agents_run":     ["code_analysis", "security", "style", "impact"],
        "phase":          3
    }
    return state

# ---- Build Graph ----
def build_review_graph():
    workflow = StateGraph(ReviewState)
    workflow.add_node("parallel_agents", parallel_agents)
    workflow.add_node("report_generator", report_generator_agent)
    workflow.set_entry_point("parallel_agents")
    workflow.add_edge("parallel_agents", "report_generator")
    workflow.add_edge("report_generator", END)
    return workflow.compile()

review_graph = build_review_graph()