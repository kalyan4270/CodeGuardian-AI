from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, review
from core.config import get_settings
from core.logging import get_logger, setup_logging
from graph.neo4j_client import neo4j_client

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    try:
        message = neo4j_client.verify_connection()
        logger.info(message)
    except Exception as exc:
        logger.warning("Neo4j connection failed: %s", exc)
    yield
    neo4j_client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CodeGuardian AI",
        description="Multi-Agent Intelligent Code Review Platform",
        version="0.4.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(review.router)
    return app


app = create_app()
