from __future__ import annotations

import io
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from agents.orchestrator import review_graph
from core.exceptions import GitHubAPIError, LLMRateLimitError, ReviewNotFoundError, TranscriptionError
from core.logging import get_logger
from models.schemas import PRRequest, ReviewResponse, TextQueryResponse
from models.state import ReviewState
from multimodal.voice_input import process_voice_query
from multimodal.voice_output import answer_voice_query, generate_voice_summary
from reports.generator import format_report
from services.github_service import fetch_pr_data
from services.report_store import report_store

router = APIRouter(prefix="/review", tags=["review"])
logger = get_logger(__name__)


def _repo_path(repo_owner: str, repo_name: str) -> str:
    return f"{repo_owner}/{repo_name}"


def _get_report_or_404(repo_owner: str, repo_name: str, pr_number: int) -> dict:
    report = report_store.get_by_path(repo_owner, repo_name, pr_number)
    if report is None:
        raise ReviewNotFoundError(_repo_path(repo_owner, repo_name), pr_number)
    return report


def _build_initial_state(pr_data: dict) -> ReviewState:
    return ReviewState(
        pr_diff=pr_data["pr_diff"],
        pr_description=pr_data["pr_description"],
        pr_title=pr_data["pr_title"],
        repo_name=pr_data["repo_name"],
        pr_number=pr_data["pr_number"],
        code_analysis="",
        security_findings="",
        style_issues="",
        impact_analysis="",
        graph_metadata={},
        final_report={},
    )


@router.post("", response_model=ReviewResponse)
async def review_pr(request: PRRequest) -> ReviewResponse:
    try:
        pr_data = await fetch_pr_data(str(request.repo_url), request.pr_number)
        logger.info("Running review pipeline for PR #%s", request.pr_number)

        result = review_graph.invoke(_build_initial_state(pr_data))
        formatted = format_report(result["final_report"])
        report_store.save(pr_data["repo_name"], request.pr_number, result["final_report"])

        return ReviewResponse(
            pr_number=request.pr_number,
            repo=pr_data["repo_name"],
            status="success",
            report=formatted,
        )
    except GitHubAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except LLMRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "message": str(exc),
                "models_tried": exc.models_tried,
                "retry_after": exc.retry_after,
                "hint": "Set GROQ_MODEL=llama-3.1-8b-instant in .env or wait for quota reset.",
            },
        ) from exc


@router.get("/{repo_owner}/{repo_name}/{pr_number}/voice-summary")
async def get_voice_summary(repo_owner: str, repo_name: str, pr_number: int) -> StreamingResponse:
    try:
        report = _get_report_or_404(repo_owner, repo_name, pr_number)
        audio_bytes, spoken_text = generate_voice_summary(report)
        logger.info("Generated voice summary: %s...", spoken_text[:100])

        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": f"attachment; filename=review_{pr_number}.mp3"},
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{repo_owner}/{repo_name}/{pr_number}/voice-query")
async def voice_query(
    repo_owner: str,
    repo_name: str,
    pr_number: int,
    audio_file: Annotated[UploadFile, File(...)],
) -> StreamingResponse:
    try:
        report = _get_report_or_404(repo_owner, repo_name, pr_number)
        audio_bytes = await audio_file.read()
        extension = (audio_file.filename or "wav").rsplit(".", 1)[-1]

        query_text = process_voice_query(audio_bytes, extension)
        answer_text, audio_response = answer_voice_query(query_text=query_text, report=report)
        logger.info("Voice query answered: %s", query_text)

        return StreamingResponse(
            io.BytesIO(audio_response),
            media_type="audio/mpeg",
            headers={"X-Query-Text": query_text, "X-Answer-Text": answer_text},
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TranscriptionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{repo_owner}/{repo_name}/{pr_number}/query", response_model=TextQueryResponse)
async def text_query(
    repo_owner: str,
    repo_name: str,
    pr_number: int,
    question: Annotated[str, Form(...)],
) -> TextQueryResponse:
    try:
        report = _get_report_or_404(repo_owner, repo_name, pr_number)
        answer_text, _ = answer_voice_query(query_text=question, report=report)

        return TextQueryResponse(
            question=question,
            answer=answer_text,
            audio_url=f"/review/{repo_owner}/{repo_name}/{pr_number}/voice-summary",
        )
    except ReviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
