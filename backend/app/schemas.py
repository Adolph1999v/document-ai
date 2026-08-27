"""Pydantic request and response contracts for the API."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    pages_with_text: int = Field(ge=1)
    chunks_stored: int = Field(ge=1)


class ChatRequest(BaseModel):
    document_id: UUID
    question: str = Field(min_length=1, max_length=2_000)


class RetrievedSource(BaseModel):
    page_number: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    similarity_score: float
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[RetrievedSource]
