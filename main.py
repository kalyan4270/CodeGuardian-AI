import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models.schemas import PRRequest, ReviewResponse
from services.github_service import fetch_pr_data
from agents.orchestrator import review_graph
from reports.generator import format_report

load_dotenv()

app = FastAPI(
    title="CodeGuardian AI",
    description="Multi-Agent Intelligent Code Review Platform",
    version="0.1.0 — Phase 1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
async def root():
    return {
        "name": "CodeGuardian AI",
        "version": "Phase 1",
        "status": "running",
        "agents_active": ["code_analysis"],
        "agents_coming": ["security", "style", "impact_analysis", "voice"]
    }

@app.post("/review", response_model=ReviewResponse)
async def review_pr(request: PRRequest):
    """
    Main endpoint. Accepts a GitHub PR and returns
    a structured AI-generated review report.
    """
    try:
        # Step 1: Fetch PR data from GitHub
        print(f"Fetching PR #{request.pr_number} from {request.repo_url}")
        pr_data = await fetch_pr_data(request.repo_url, request.pr_number)

        # Step 2: Build initial state for LangGraph
        initial_state = {
            "pr_diff":           pr_data["pr_diff"],
            "pr_description":    pr_data["pr_description"],
            "pr_title":          pr_data["pr_title"],
            "repo_name":         pr_data["repo_name"],
            "pr_number":         pr_data["pr_number"],
            "code_analysis":     "",
            "security_findings": "",   # NEW
            "style_issues":      "",   # NEW
            "impact_analysis":   "",   # NEW
            "final_report":      {}
        }

        # Step 3: Run through LangGraph agent pipeline
        print("Running review agents...")
        result = review_graph.invoke(initial_state)

        # Step 4: Format and return report
        formatted = format_report(result["final_report"])

        return ReviewResponse(
            pr_number=request.pr_number,
            repo=pr_data["repo_name"],
            status="success",
            report=formatted
        )

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"GitHub API error: {e.response.text}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "phase": 1}