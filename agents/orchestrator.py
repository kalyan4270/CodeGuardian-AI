import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from groq import Groq
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

from agents.security_agent import security_agent
from agents.style_agent import style_agent

# ---- Updated State — new fields added ----
class ReviewState(TypedDict):
    pr_diff: str
    pr_description: str
    pr_title: str
    repo_name: str
    pr_number: int
    code_analysis: str
    security_findings: str
    style_issues: str
    impact_analysis: str    # Phase 3
    final_report: dict

# ---- Agent: Code Analysis (same as Phase 1) ----
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

    Be specific and reference line numbers where possible.
    Keep your response concise and actionable.
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

# ---- Parallel Agent Runner ----
def parallel_agents(state: ReviewState) -> ReviewState:
    """
    Runs code, security, and style agents in parallel
    using ThreadPoolExecutor.
    All three run simultaneously — faster than sequential.
    """
    with ThreadPoolExecutor(max_workers=3) as executor:

        # Submit all 3 agents simultaneously
        code_future     = executor.submit(code_analysis_agent, state.copy())
        security_future = executor.submit(security_agent, state.copy())
        style_future    = executor.submit(style_agent, state.copy())

        # Wait for all to complete
        code_result     = code_future.result()
        security_result = security_future.result()
        style_result    = style_future.result()

    # Merge results back into state
    state["code_analysis"]     = code_result["code_analysis"]
    state["security_findings"] = security_result["security_findings"]
    state["style_issues"]      = style_result["style_issues"]
    state["impact_analysis"]   = "Coming in Phase 3 — Neo4j integration"

    return state

# ---- Report Generator (updated) ----
def report_generator_agent(state: ReviewState) -> ReviewState:
    """
    Compiles all agent outputs into final structured report.
    """
    # Generate overall summary using LLM
    summary_prompt = f"""
    Based on the following code review findings, write a 2-3 sentence
    executive summary of this pull request review:

    Code Analysis: {state['code_analysis'][:500]}
    Security Findings: {state['security_findings'][:300]}
    Style Issues: {state['style_issues'][:300]}

    Be concise. Mention the most critical issues first.
    """

    summary_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": summary_prompt}],
        max_tokens=256,
        temperature=0.3
    )

    state["final_report"] = {
        "pr_number": state["pr_number"],
        "repo": state["repo_name"],
        "pr_title": state["pr_title"],
        "executive_summary": summary_response.choices[0].message.content,
        "summary": {
            "code_analysis":     state["code_analysis"],
            "security_findings": state["security_findings"],
            "style_issues":      state["style_issues"],
            "impact_analysis":   state["impact_analysis"],
        },
        "status": "completed",
        "agents_run": ["code_analysis", "security", "style"],
        "phase": 2
    }
    return state

# ---- Build Updated LangGraph ----
def build_review_graph():
    """
    Phase 2 graph:
    parallel_agents (runs all 3 simultaneously) → report_generator
    """
    workflow = StateGraph(ReviewState)

    # Single node that runs all agents in parallel
    workflow.add_node("parallel_agents", parallel_agents)
    workflow.add_node("report_generator", report_generator_agent)

    workflow.set_entry_point("parallel_agents")
    workflow.add_edge("parallel_agents", "report_generator")
    workflow.add_edge("report_generator", END)

    return workflow.compile()

review_graph = build_review_graph()