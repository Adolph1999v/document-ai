-- Document AI's clean RAG table. Requires PostgreSQL with pgvector installed.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL,
    filename TEXT NOT NULL,
    page_number INTEGER NOT NULL CHECK (page_number > 0),
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS document_chunks_document_id_idx
    ON document_chunks (document_id);

-- Start with exact search while the learning corpus is small. When you have a
-- meaningful amount of data and an evaluation set, compare this HNSW index
-- against the baseline before enabling it:
--
-- CREATE INDEX document_chunks_embedding_hnsw_idx
--     ON document_chunks USING hnsw (embedding vector_cosine_ops);
