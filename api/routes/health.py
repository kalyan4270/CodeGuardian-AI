from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def root() -> dict:
    return {
        "name": "CodeGuardian AI",
        "version": "Phase 4",
        "status": "running",
        "agents_active": ["code_analysis", "security", "style", "impact"],
        "features": ["multi_agent", "neo4j_graph", "voice_input", "voice_output"],
    }


@router.get("/health", response_model=None)
async def health() -> dict:
    return {
        "status": "healthy",
        "phase": 4,
        "features": {
            "agents": True,
            "neo4j": True,
            "voice_input": True,
            "voice_output": True,
        },
    }
