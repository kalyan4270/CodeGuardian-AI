"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PRRequest(BaseModel):
    repo_url: HttpUrl | str = Field(
        ...,
        description="GitHub repository URL, e.g. https://github.com/owner/repo",
        examples=["https://github.com/owner/repo"],
    )
    pr_number: int = Field(..., ge=1, description="Pull request number")


class ReviewResponse(BaseModel):
    pr_number: int
    repo: str
    status: str
    report: dict[str, Any]


class TextQueryResponse(BaseModel):
    question: str
    answer: str
    audio_url: str


class HealthResponse(BaseModel):
    status: str
    phase: int
    features: dict[str, bool]
