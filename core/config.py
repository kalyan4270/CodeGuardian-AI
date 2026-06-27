"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    groq_api_key: str
    github_token: str
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_fallback_models: tuple[str, ...] = ("llama-3.1-8b-instant",)
    max_diff_chars: int = 6_000
    cors_origins: tuple[str, ...] = ("*",)

    @classmethod
    def from_env(cls) -> Settings:
        fallback_raw = os.getenv("GROQ_FALLBACK_MODELS", "llama-3.1-8b-instant")
        fallback_models = tuple(m.strip() for m in fallback_raw.split(",") if m.strip())

        return cls(
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            neo4j_uri=os.getenv("NEO4J_URI", ""),
            neo4j_username=os.getenv("NEO4J_USERNAME", ""),
            neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            groq_fallback_models=fallback_models,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()
