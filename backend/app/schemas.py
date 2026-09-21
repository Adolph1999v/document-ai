"""Pydantic request and response contracts for the API."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class DependencyReadinessResponse(BaseModel):
    ready: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: DependencyReadinessResponse
    local_model: DependencyReadinessResponse


# Upload responses expose enough ingestion metadata for the client to confirm
# which document was indexed before it begins sending questions.
class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    pages_with_text: int = Field(ge=1)
    chunks_stored: int = Field(ge=1)


# Each chat request is scoped to one previously indexed document.
class ChatRequest(BaseModel):
    document_id: UUID
    question: str = Field(min_length=1, max_length=2_000)


# Retrieved evidence stays structured so the UI can present source details
# independently from the generated answer text.
class RetrievedSource(BaseModel):
    page_number: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    similarity_score: float
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[RetrievedSource]
