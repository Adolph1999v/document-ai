"""Configuration lives in environment variables, never in application code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
# Load machine-local values before the cached Settings object is constructed.
# Existing process environment variables keep priority over values in this file.
load_dotenv(BACKEND_DIRECTORY / ".env")


def _read_int(name: str, default: int) -> int:
    """Read a positive integer setting and fail early for invalid values."""

    value = os.getenv(name, str(default))
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer, received {value!r}.") from error

    if parsed_value <= 0:
        raise ValueError(f"{name} must be greater than zero.")

    return parsed_value


def _read_origins() -> tuple[str, ...]:
    """Convert the comma-separated CORS setting into validated origins."""

    configured_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    origins = tuple(origin.strip() for origin in configured_origins.split(",") if origin.strip())
    if not origins:
        raise ValueError("CORS_ORIGINS must contain at least one origin.")
    return origins


def _read_local_llm_base_url() -> str:
    """Accept only a loopback LM Studio endpoint for local-only generation."""

    value = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234/api/v1").rstrip("/")
    parsed_url = urlparse(value)
    if parsed_url.scheme != "http" or parsed_url.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError(
            "LOCAL_LLM_BASE_URL must be an HTTP endpoint on localhost or a loopback address."
        )
    return value


@dataclass(frozen=True)
class Settings:
    """The small, explicit configuration surface of this first RAG foundation."""

    app_name: str
    local_llm_base_url: str
    local_llm_model: str
    local_llm_timeout_seconds: int
    local_llm_context_length: int
    local_llm_max_output_tokens: int
    local_llm_reasoning: str
    database_host: str
    database_port: int
    database_name: str
    database_user: str
    database_password: str | None
    cors_origins: tuple[str, ...]
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    retrieval_top_k: int
    max_upload_size_bytes: int

    @property
    def database_connection_parameters(self) -> dict[str, str | int]:
        """Expose only the values required when opening a database connection."""

        parameters: dict[str, str | int] = {
            "host": self.database_host,
            "port": self.database_port,
            "dbname": self.database_name,
            "user": self.database_user,
        }
        if self.database_password:
            parameters["password"] = self.database_password
        return parameters


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build settings once per process so every layer shares the same contract."""

    chunk_size = _read_int("CHUNK_SIZE", 900)
    chunk_overlap = _read_int("CHUNK_OVERLAP", 150)
    if chunk_overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE.")

    local_llm_reasoning = os.getenv("LOCAL_LLM_REASONING", "off").strip().lower()
    if local_llm_reasoning not in {"off", "on"}:
        raise ValueError("LOCAL_LLM_REASONING must be either 'off' or 'on'.")

    return Settings(
        app_name="Document AI",
        local_llm_base_url=_read_local_llm_base_url(),
        local_llm_model=os.getenv("LOCAL_LLM_MODEL", "qwen/qwen3.6-27b"),
        local_llm_timeout_seconds=_read_int("LOCAL_LLM_TIMEOUT_SECONDS", 300),
        local_llm_context_length=_read_int("LOCAL_LLM_CONTEXT_LENGTH", 32_768),
        local_llm_max_output_tokens=_read_int("LOCAL_LLM_MAX_OUTPUT_TOKENS", 800),
        local_llm_reasoning=local_llm_reasoning,
        database_host=os.getenv("DATABASE_HOST", "127.0.0.1"),
        database_port=_read_int("DATABASE_PORT", 5432),
        database_name=os.getenv("DATABASE_NAME", "document_ai"),
        database_user=os.getenv("DATABASE_USER", "postgres"),
        database_password=os.getenv("DATABASE_PASSWORD") or None,
        cors_origins=_read_origins(),
        embedding_model=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        retrieval_top_k=_read_int("RETRIEVAL_TOP_K", 4),
        max_upload_size_bytes=_read_int("MAX_UPLOAD_SIZE_MB", 20) * 1024 * 1024,
    )


settings = get_settings()
