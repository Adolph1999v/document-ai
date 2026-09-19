"""FastAPI application: HTTP concerns stay separate from RAG mechanics."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import psycopg2
from fastapi import FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import DatabaseConnectionError, check_database_readiness
from .local_llm import (
    LocalModelResponseError,
    LocalModelUnavailableError,
    get_local_llm_client,
)
from .rag import (
    DocumentNotFoundError,
    DocumentProcessingError,
    extract_chunks,
    generate_answer,
    index_document,
    retrieve_chunks,
)
from .schemas import (
    ChatRequest,
    ChatResponse,
    DependencyReadinessResponse,
    DocumentUploadResponse,
    HealthResponse,
    ReadinessResponse,
    RetrievedSource,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="A learning-focused, production-minded RAG chatbot for PDFs.",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"message": "Document AI API is running."}


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get(
    "/api/readiness",
    response_model=ReadinessResponse,
    tags=["system"],
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def readiness_check(response: Response) -> ReadinessResponse:
    """Report whether both external runtime dependencies can serve requests."""

    database = check_database_readiness()
    local_model = get_local_llm_client().check_readiness()
    is_ready = database.ready and local_model.ready
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        database=DependencyReadinessResponse(
            ready=database.ready,
            detail=database.detail,
        ),
        local_model=DependencyReadinessResponse(
            ready=local_model.ready,
            detail=local_model.detail,
        ),
    )


@app.post(
    "/api/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
)
def upload_document(file: Annotated[UploadFile, File(...)]) -> DocumentUploadResponse:
    """Index one text-based PDF and return an identifier for later chat requests."""

    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    pdf_bytes = file.file.read(settings.max_upload_size_bytes + 1)
    if len(pdf_bytes) > settings.max_upload_size_bytes:
        maximum_megabytes = settings.max_upload_size_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"PDFs must be {maximum_megabytes} MB or smaller.",
        )

    try:
        chunks, pages_with_text = extract_chunks(pdf_bytes)
        document_id = index_document(filename, chunks)
    except DocumentProcessingError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except DatabaseConnectionError as error:
        logger.exception("Database connection failed while indexing a document.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except psycopg2.Error as error:
        logger.exception("Database error while indexing a document.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document store is not ready. Check that backend/sql/schema.sql was applied.",
        ) from error

    return DocumentUploadResponse(
        document_id=document_id,
        filename=filename,
        pages_with_text=pages_with_text,
        chunks_stored=len(chunks),
    )


@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
def chat(request: ChatRequest) -> ChatResponse:
    """Answer one question using only chunks retrieved for the chosen document."""

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A question cannot be blank.",
        )

    try:
        retrieved_chunks = retrieve_chunks(request.document_id, question)
        answer = generate_answer(question, retrieved_chunks)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LocalModelUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except LocalModelResponseError as error:
        logger.exception("The local language model returned an invalid answer.")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except DatabaseConnectionError as error:
        logger.exception("Database connection failed while retrieving context.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)
        ) from error
    except psycopg2.Error as error:
        logger.exception("Database error while retrieving context.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document store is not ready. Check that backend/sql/schema.sql was applied.",
        ) from error

    return ChatResponse(
        answer=answer,
        sources=[
            RetrievedSource(
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                similarity_score=round(chunk.similarity_score, 3),
                excerpt=chunk.content,
            )
            for chunk in retrieved_chunks
        ],
    )
