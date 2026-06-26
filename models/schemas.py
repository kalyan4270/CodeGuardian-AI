from pydantic import BaseModel

class PRRequest(BaseModel):
    repo_url: str        # e.g. "https://github.com/user/repo"
    pr_number: int       # e.g. 42

class ReviewState(dict):
    """
    LangGraph state shared across all agents.
    Each agent reads from and writes to this state.
    """
    pr_diff: str
    pr_description: str
    repo_name: str
    pr_number: int
    code_analysis: str
    final_report: dict

class ReviewResponse(BaseModel):
    pr_number: int
    repo: str
    status: str
    report: dict