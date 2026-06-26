import os
from typing import TypedDict
from langgraph.graph import StateGraph, END
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---- State Definition ----
class ReviewState(TypedDict):
    pr_diff: str
    pr_description: str
    pr_title: str
    repo_name: str
    pr_number: int
    code_analysis: str
    final_report: dict

# ---- Agent: Code Analysis ----
def code_analysis_agent(state: ReviewState) -> ReviewState:
    """
    Analyses the PR diff for bugs, logic issues,
    and inefficient code using Groq LLM.
    """
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
        model="llama3-70b-8192",  # best free model on Groq
        # alternatives if you hit rate limits:
        # model="llama3-8b-8192"      # faster, lighter
        # model="mixtral-8x7b-32768"  # good for code
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.3
    )

    state["code_analysis"] = response.choices[0].message.content
    return state

# ---- Agent: Report Generator ----
def report_generator_agent(state: ReviewState) -> ReviewState:
    """
    Compiles all agent outputs into a structured report.
    In Phase 1 this only has code analysis.
    In Phase 2+ it will include security, style, impact.
    """
    state["final_report"] = {
        "pr_number": state["pr_number"],
        "repo": state["repo_name"],
        "pr_title": state["pr_title"],
        "summary": {
            "code_analysis": state["code_analysis"],
            # Phase 2: security_findings will go here
            # Phase 2: style_issues will go here
            # Phase 3: impact_analysis will go here
        },
        "status": "completed"
    }
    return state

# ---- Build LangGraph ----
def build_review_graph():
    """
    Builds the LangGraph state machine.
    Phase 1: linear flow — code agent → report agent
    Phase 2: will add parallel branches for all agents
    """
    workflow = StateGraph(ReviewState)

    # Add nodes (agents)
    workflow.add_node("code_analyzer", code_analysis_agent)
    workflow.add_node("report_generator", report_generator_agent)

    # Define flow
    workflow.set_entry_point("code_analyzer")
    workflow.add_edge("code_analyzer", "report_generator")
    workflow.add_edge("report_generator", END)

    return workflow.compile()

# Single compiled graph instance
review_graph = build_review_graph()