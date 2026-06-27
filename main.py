import os
import httpx
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import io

from models.schemas import PRRequest, ReviewResponse
from services.github_service import fetch_pr_data
from agents.orchestrator import review_graph
from reports.generator import format_report
from graph.neo4j_client import neo4j_client
from multimodal.voice_input import process_voice_query
from multimodal.voice_output import generate_voice_summary, answer_voice_query

load_dotenv()

app = FastAPI(
    title="CodeGuardian AI",
    description="Multi-Agent Intelligent Code Review Platform",
    version="0.4.0 — Phase 4"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Store last report in memory for voice queries
# Phase 5 will move this to a proper database
last_reports = {}

@app.on_event("startup")
async def startup():
    try:
        msg = neo4j_client.verify_connection()
        print(f"{msg}")
    except Exception as e:
        print(f"Neo4j connection failed: {e}")

@app.get("/")
async def root():
    return {
        "name":          "CodeGuardian AI",
        "version":       "Phase 4",
        "status":        "running",
        "agents_active": ["code_analysis", "security", "style", "impact"],
        "features":      ["multi_agent", "neo4j_graph", "voice_input", "voice_output"]
    }

# ─── Endpoint 1: Review PR ──────────────────────────────
@app.post("/review", response_model=ReviewResponse)
async def review_pr(request: PRRequest):
    """
    Main endpoint. Accepts GitHub PR and returns
    structured AI review report.
    """
    try:
        # Step 1: Fetch PR data
        print(f"Fetching PR #{request.pr_number} from {request.repo_url}")
        pr_data = await fetch_pr_data(request.repo_url, request.pr_number)

        # Step 2: Build initial state
        initial_state = {
            "pr_diff":           pr_data["pr_diff"],
            "pr_description":    pr_data["pr_description"],
            "pr_title":          pr_data["pr_title"],
            "repo_name":         pr_data["repo_name"],
            "pr_number":         pr_data["pr_number"],
            "code_analysis":     "",
            "security_findings": "",
            "style_issues":      "",
            "impact_analysis":   "",
            "graph_metadata":    {},
            "final_report":      {}
        }

        # Step 3: Run agent pipeline
        print("Running 4 agents in parallel...")
        result = review_graph.invoke(initial_state)

        # Step 4: Format report
        formatted = format_report(result["final_report"])

        # Step 5: Store report for voice queries
        report_key = f"{pr_data['repo_name']}_{request.pr_number}"
        last_reports[report_key] = result["final_report"]

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

# ─── Endpoint 2: Voice Summary ──────────────────────────
@app.get("/review/{repo_owner}/{repo_name}/{pr_number}/voice-summary")
async def get_voice_summary(repo_owner: str,
                             repo_name: str,
                             pr_number: int):
    """
    Returns audio file of spoken review summary.
    Call this after /review to get voice output.
    """
    report_key = f"{repo_owner}/{repo_name}_{pr_number}"
    report     = last_reports.get(report_key)

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Review not found. Run /review first."
        )

    try:
        audio_bytes, spoken_text = generate_voice_summary(report)

        print(f"Generated voice summary: {spoken_text[:100]}...")

        # Return audio as streaming MP3 response
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=review_{pr_number}.mp3"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Endpoint 3: Voice Query ────────────────────────────
@app.post("/review/{repo_owner}/{repo_name}/{pr_number}/voice-query")
async def voice_query(repo_owner: str,
                      repo_name:  str,
                      pr_number:  int,
                      audio_file: UploadFile = File(...)):
    """
    Developer asks a voice question about the review.
    Upload audio file → get spoken answer back.

    Example questions:
    - "What are the security issues?"
    - "Which files are impacted?"
    - "What should I fix first?"
    """
    report_key = f"{repo_owner}/{repo_name}_{pr_number}"
    report     = last_reports.get(report_key)

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Review not found. Run /review first."
        )

    try:
        # Step 1: Read uploaded audio
        audio_bytes     = await audio_file.read()
        file_extension  = audio_file.filename.split(".")[-1]

        # Step 2: Transcribe voice to text
        print(f"Transcribing audio: {audio_file.filename}")
        query_text = process_voice_query(audio_bytes, file_extension)
        print(f"Question: {query_text}")

        # Step 3: Generate answer + convert to speech
        answer_text, audio_response = answer_voice_query(
            query_text=query_text,
            report=report
        )
        print(f"Answer: {answer_text}")

        # Step 4: Return audio answer
        return StreamingResponse(
            io.BytesIO(audio_response),
            media_type="audio/mpeg",
            headers={
                "X-Query-Text":  query_text,
                "X-Answer-Text": answer_text
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Endpoint 4: Text Query (fallback) ─────────────────
@app.post("/review/{repo_owner}/{repo_name}/{pr_number}/query")
async def text_query(repo_owner: str,
                     repo_name:  str,
                     pr_number:  int,
                     question:   str = Form(...)):
    """
    Text version of voice query — for testing without audio.
    Same logic, returns JSON instead of audio.
    """
    report_key = f"{repo_owner}/{repo_name}_{pr_number}"
    report     = last_reports.get(report_key)

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Review not found. Run /review first."
        )

    try:
        answer_text, audio_bytes = answer_voice_query(
            query_text=question,
            report=report
        )
        return {
            "question":     question,
            "answer":       answer_text,
            "audio_url":    f"/review/{repo_owner}/{repo_name}/{pr_number}/voice-summary"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "phase":  4,
        "features": {
            "agents":       True,
            "neo4j":        True,
            "voice_input":  True,
            "voice_output": True
        }
    }