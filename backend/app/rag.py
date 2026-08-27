"""RAG building blocks: ingest, embed, retrieve, and generate."""

from __future__ import annotations

import io
import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID, uuid4

import pdfplumber
from google import genai
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

from .config import settings
from .database import get_database_connection


class DocumentProcessingError(ValueError):
    """The uploaded file could not be processed as a useful PDF."""


class DocumentNotFoundError(ValueError):
    """The requested document has no indexed chunks."""


class GenerationConfigurationError(RuntimeError):
    """The service is missing the configuration needed to call Gemini."""


class AnswerGenerationError(RuntimeError):
    """Gemini returned no usable text for a valid request."""


@dataclass(frozen=True)
class TextChunk:
    page_number: int
    chunk_index: int
    content: str


@dataclass(frozen=True)
class RetrievedChunk:
    page_number: int
    chunk_index: int
    content: str
    similarity_score: float


def clean_text(text: str) -> str:
    """Normalize extraction artifacts without trying to rewrite document meaning."""

    normalized = re.sub(r"\s+", " ", text)
    normalized = re.sub(r"([a-z])([A-Z])", r"\1 \2", normalized)
    normalized = re.sub(r"([.,!?])([A-Za-z])", r"\1 \2", normalized)
    return normalized.strip()


def _split_text(text: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text on a nearby natural boundary while preserving small overlap."""

    chunks: list[str] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end < text_length:
            preferred_break = text.rfind(". ", start + chunk_size // 2, end)
            fallback_break = text.rfind(" ", start + chunk_size // 2, end)
            boundary = max(preferred_break + 1, fallback_break)
            if boundary > start:
                end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(end - chunk_overlap, start + 1)
        while next_start < text_length and text[next_start].isspace():
            next_start += 1
        start = next_start

    return chunks


def extract_chunks(pdf_bytes: bytes) -> tuple[list[TextChunk], int]:
    """Extract page-aware chunks from a PDF so answers can point back to a page."""

    chunks: list[TextChunk] = []
    pages_with_text = 0

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = clean_text(page.extract_text() or "")
                if not page_text:
                    continue

                pages_with_text += 1
                page_chunks = _split_text(
                    page_text,
                    chunk_size=settings.chunk_size,
                    chunk_overlap=settings.chunk_overlap,
                )
                chunks.extend(
                    TextChunk(
                        page_number=page_number,
                        chunk_index=chunk_index,
                        content=chunk,
                    )
                    for chunk_index, chunk in enumerate(page_chunks)
                )
    except Exception as error:  # pdfplumber surfaces several parser exception types.
        raise DocumentProcessingError("The uploaded file could not be read as a PDF.") from error

    if not chunks:
        raise DocumentProcessingError(
            "No selectable text was found. This may be a scanned PDF that needs OCR."
        )

    return chunks, pages_with_text


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once, not for every upload or question."""

    return SentenceTransformer(settings.embedding_model)


def _embed_texts(texts: Iterable[str]) -> list[list[float]]:
    embeddings = get_embedding_model().encode(
        list(texts),
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [embedding.tolist() for embedding in embeddings]


def _to_vector_literal(values: Iterable[float]) -> str:
    """Represent a Python vector in the text format accepted by pgvector."""

    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def index_document(filename: str, chunks: list[TextChunk]) -> UUID:
    """Embed and store all chunks for one uploaded document."""

    document_id = uuid4()
    embeddings = _embed_texts(chunk.content for chunk in chunks)
    rows = [
        (
            str(document_id),
            filename,
            chunk.page_number,
            chunk.chunk_index,
            chunk.content,
            _to_vector_literal(embedding),
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            execute_values(
                cursor,
                """
                INSERT INTO document_chunks
                    (document_id, filename, page_number, chunk_index, content, embedding)
                VALUES %s
                """,
                rows,
                template="(%s::uuid, %s, %s, %s, %s, %s::vector)",
            )
        connection.commit()

    return document_id


def retrieve_chunks(document_id: UUID, question: str) -> list[RetrievedChunk]:
    """Retrieve the most semantically similar chunks for one document only."""

    question_embedding = _to_vector_literal(_embed_texts([question])[0])

    with get_database_connection() as connection, connection.cursor() as cursor:
        cursor.execute(
            """
                SELECT
                    page_number,
                    chunk_index,
                    content,
                    1 - (embedding <=> %s::vector) AS similarity_score
                FROM document_chunks
                WHERE document_id = %s::uuid
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
            (
                question_embedding,
                str(document_id),
                question_embedding,
                settings.retrieval_top_k,
            ),
        )
        results = cursor.fetchall()

    if not results:
        raise DocumentNotFoundError(
            "No indexed content was found for this document. Upload it again and try once more."
        )

    return [
        RetrievedChunk(
            page_number=row[0],
            chunk_index=row[1],
            content=row[2],
            similarity_score=float(row[3]),
        )
        for row in results
    ]


@lru_cache(maxsize=1)
def get_gemini_client() -> genai.Client:
    """Create the Gemini client only when generation is actually requested."""

    if not settings.google_api_key:
        raise GenerationConfigurationError(
            "GOOGLE_API_KEY is not configured. Add it to backend/.env before asking questions."
        )
    return genai.Client(api_key=settings.google_api_key)


def generate_answer(question: str, sources: list[RetrievedChunk]) -> str:
    """Ask Gemini to answer only from retrieved evidence and cite pages."""

    context = "\n\n".join(
        f"[Page {source.page_number}]\n{source.content}" for source in sources
    )
    prompt = f"""
You are Document AI, a precise retrieval-augmented assistant.

Answer the question using only the supplied document context. If the context does
not support an answer, say that clearly instead of guessing. When you make a
claim, cite the relevant source in the form [Page N]. Keep the answer concise,
clear, and helpful.

Document context:
{context}

Question:
{question}
""".strip()

    response = get_gemini_client().models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config={"temperature": 0.2},
    )
    answer = getattr(response, "text", None)

    if not answer or not answer.strip():
        raise AnswerGenerationError("The language model did not return a usable answer.")

    return answer.strip()
