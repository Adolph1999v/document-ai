"""Configuration lives in environment variables, never in application code."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

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

    configured_origins = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    origins = tuple(origin.strip() for origin in configured_origins.split(",") if origin.strip())
    if not origins:
        raise ValueError("CORS_ORIGINS must contain at least one origin.")
    return origins


@dataclass(frozen=True)
class Settings:
    """The small, explicit configuration surface of this first RAG foundation."""

    app_name: str
    google_api_key: str | None
    gemini_model: str
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

    return Settings(
        app_name="Document AI",
        google_api_key=os.getenv("GOOGLE_API_KEY") or None,
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
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
