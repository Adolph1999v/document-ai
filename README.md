# Document AI

Document AI is a learning-focused, production-minded Retrieval-Augmented Generation (RAG) chatbot for PDF documents. It lets a user upload a PDF, ask questions about that document, retrieve the most relevant passages, and use an LLM to produce an answer grounded in those passages.

This repository is intentionally evolving in public: each phase should make the system more capable **and** make the RAG concepts behind it easier to understand.

## What it does today

- Accepts a PDF through a React web interface.
- Extracts page text with `pdfplumber`.
- Cleans and splits text into overlapping, page-aware chunks.
- Embeds chunks with the `all-MiniLM-L6-v2` sentence-transformer model.
- Stores chunks and embeddings in PostgreSQL with the `pgvector` extension.
- Retrieves the most similar chunks for a question using cosine distance.
- Sends the retrieved context to Google Gemini and returns an answer with page references.

## The RAG flow

```text
PDF upload
   │
   ├─ Extract text page by page
   ├─ Clean + chunk text with overlap
   ├─ Create embeddings
   └─ Store chunks, metadata, and vectors in PostgreSQL/pgvector

Question
   │
   ├─ Create a question embedding
   ├─ Retrieve the nearest chunks for that document
   ├─ Build grounded context for Gemini
   └─ Return an answer + source page metadata to the UI
```

RAG stands for **Retrieval-Augmented Generation**. Retrieval gives the model relevant evidence from a document; generation turns that evidence into a useful answer. The language model does not search the PDF by itself—the retrieval layer decides what context it sees.

## Tech stack

| Area | Technology | Why it is here |
| --- | --- | --- |
| Frontend | React 19 + Vite | A fast, modern development workflow and a responsive chat interface. |
| API | FastAPI | Typed Python endpoints with automatic API documentation. |
| PDF ingestion | pdfplumber | Extracts text while retaining page boundaries. |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) | Converts text into 384-dimensional semantic vectors. |
| Vector store | PostgreSQL + pgvector | Keeps document metadata and vectors in one familiar database. |
| Answer generation | Google Gemini | Produces a natural-language answer from retrieved context. |

## Project layout

```text
document_ai/
├── Makefile                # Common setup, run, test, and build commands
├── backend/
│   ├── app/
│   │   ├── config.py       # Environment-based settings
│   │   ├── database.py     # PostgreSQL connection boundary
│   │   ├── main.py         # FastAPI routes and HTTP handling
│   │   ├── rag.py          # Ingestion, embedding, retrieval, generation
│   │   └── schemas.py      # Request/response contracts
│   ├── sql/schema.sql      # pgvector table definition
│   ├── .env.example
│   ├── pyproject.toml      # Dependency source of truth
│   ├── requirements.txt
│   └── uv.lock             # Exact resolved backend dependencies
└── frontend/
    ├── src/
    │   ├── api.js          # API client
    │   ├── App.jsx         # Upload and chat experience
    │   └── *.css           # Responsive UI styles
    └── vite.config.js
```

## Run it locally

### Prerequisites

- `uv` (it will provision the pinned Python 3.13 runtime automatically)
- Python 3.11–3.13 if you prefer to provide the interpreter yourself
- Node.js 20.19+ (the current Vite baseline)
- PostgreSQL with the `pgvector` extension installed
- A Google AI API key with access to the selected Gemini model

### 1. Configure PostgreSQL

Create a database named `document_ai`, then run the schema once:

```bash
psql -d document_ai -f backend/sql/schema.sql
```

The schema creates a new `document_chunks` table. It does not alter the older prototype table, so the cleanup is safe to adopt without deleting prior experiments.

### 2. Configure and run the backend

```bash
cd backend
uv sync --all-groups
cp .env.example .env
uv run uvicorn main:app --reload
```

Fill in `backend/.env` before starting the server—especially `GOOGLE_API_KEY` and the database values. Do not commit that file.

The API runs on `http://127.0.0.1:8000`, and interactive FastAPI documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Run the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the frontend at `http://localhost:5173`. During local development, `/api` requests are proxied to the FastAPI server. For a separately hosted frontend, set `VITE_API_BASE_URL` in `frontend/.env`.

### Why use `uv`?

`uv` is a Rust-based Python package manager and project tool. It resolves and installs packages quickly while keeping everything inside `backend/.venv`, so this project's versions do not conflict with globally installed Python packages. `backend/pyproject.toml` is the source of truth, `backend/.python-version` selects Python 3.13, `backend/uv.lock` pins the exact resolved versions, and `backend/requirements.txt` remains available for tools that expect the traditional pip format.

You can use the root `Makefile` for common tasks after setup: `make setup`, `make backend-run`, `make frontend-run`, `make test`, `make lint`, and `make build`.

## API contract

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Lightweight service health check. |
| `POST` | `/api/documents` | Upload and index one PDF. Returns a `document_id`. |
| `POST` | `/api/chat` | Ask a question scoped to a `document_id`. Returns an answer and source metadata. |

Scoping chat requests with a `document_id` is deliberate: it replaces the old process-global “last uploaded file” approach, which could mix documents between browser sessions.

## Current scope and intentional limitations

This is now a clean RAG foundation, not a finished enterprise retrieval system. It does not yet include OCR for scanned PDFs, hybrid keyword/vector search, reranking, conversational memory, ingestion queues, user accounts, automated evaluation, tracing, or production deployment.

Those are valuable next steps, but each adds a new concept. We will introduce them in a measured order so the architecture remains understandable.

## Suggested learning roadmap

1. **Measure the baseline** — create a small question-and-answer evaluation set for a few documents and learn how to judge retrieval quality separately from answer quality.
2. **Improve ingestion** — handle scanned PDFs/OCR, headings, tables, metadata, and better semantic chunking.
3. **Improve retrieval** — add metadata filters, hybrid search, query rewriting, and reranking; compare each change against the baseline.
4. **Improve answers** — expose citations, abstain when evidence is weak, stream responses, and introduce conversation-aware retrieval carefully.
5. **Make it operational** — add tests, observability, rate limits, async ingestion, authentication, and deployment.

The rule for this project: every new RAG technique should answer a clear question—**what failure mode does it solve, and how will we prove that it helped?**
