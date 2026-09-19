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
- Sends the retrieved context to a local Qwen 27B model through LM Studio.
- Returns the grounded answer together with page references and retrieved evidence.

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
   ├─ Build grounded context for local Qwen
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
| Local inference | LM Studio | Runs the generation model behind a loopback-only REST interface. |
| Answer generation | Qwen 3.6 27B (`Q6_K`) | Produces grounded answers locally without provider quotas. |

## Project layout

```text
document_ai/
├── compose.yaml            # Reproducible local PostgreSQL/pgvector service
├── Makefile                # Common setup, run, test, and build commands
├── PLAN.md                 # Living, phase-by-phase learning and development roadmap
├── backend/
│   ├── app/
│   │   ├── config.py       # Environment-based settings
│   │   ├── database.py     # PostgreSQL connection boundary
│   │   ├── local_llm.py    # LM Studio/Qwen client and readiness boundary
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
- Docker Desktop for the reproducible PostgreSQL/pgvector service
- LM Studio with its `lms` command-line tool
- The local `qwen/qwen3.6-27b` model downloaded in LM Studio

No external model account or API key is required.

### 1. Install project dependencies

```bash
make setup
cp backend/.env.example backend/.env
```

The `.env` file is machine-local and ignored by Git. The checked-in example already matches the
development database and LM Studio defaults.

### 2. Start PostgreSQL and pgvector

Start Docker Desktop, then run:

```bash
make db-up
make db-status
```

The first start creates the `document_ai` database, enables pgvector, and applies
`backend/sql/schema.sql`. The database is bound only to `127.0.0.1`. To reapply the idempotent
schema later, run `make db-init`. Use `make db-stop` to stop PostgreSQL without deleting its data.

### 3. Start LM Studio and load Qwen

Start LM Studio's local server from its Developer tab, or run:

```bash
make model-server
make model-load
make model-status
```

If the server is already running, skip `make model-server`. The project loads Qwen with a 32,768
token context window. LM Studio estimates about 28.5 GiB for this configuration on the development
Mac, leaving headroom instead of attempting the model's much larger maximum context.

Generation requests stay on `127.0.0.1:1234`, disable model-side reasoning for the first measured
RAG baseline, and do not ask LM Studio to store chat state.

When development is finished, run `make model-unload` to free the memory used by Qwen and then
`make model-server-stop` to stop the local endpoint. These are separate actions: stopping the
server alone does not unload model weights that are already in memory.

### 4. Start and check the backend

```bash
make backend-run
```

The API runs on `http://127.0.0.1:8000`, and interactive FastAPI documentation is available at `http://127.0.0.1:8000/docs`.

In another terminal, verify both runtime dependencies:

```bash
make readiness
```

`/api/health` reports whether FastAPI itself is alive. `/api/readiness` separately checks whether
PostgreSQL is accepting queries and whether the configured Qwen model is loaded.

### 5. Run the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the frontend at `http://localhost:5173`. During local development, `/api` requests are proxied to the FastAPI server. For a separately hosted frontend, set `VITE_API_BASE_URL` in `frontend/.env`.

### Why use `uv`?

`uv` is a Rust-based Python package manager and project tool. It resolves and installs packages quickly while keeping everything inside `backend/.venv`, so this project's versions do not conflict with globally installed Python packages. `backend/pyproject.toml` is the source of truth, `backend/.python-version` selects Python 3.13, `backend/uv.lock` pins the exact resolved versions, and `backend/requirements.txt` remains available for tools that expect the traditional pip format.

You can use the root `Makefile` for dependency setup, database lifecycle, local-model loading,
readiness checks, development servers, tests, linting, and frontend builds. Run `make help` for
the complete list.

### Why local Qwen?

Local generation allows repeated experiments without provider quotas and keeps retrieved document
context on the machine. The model weights and inference runtime remain separate from FastAPI:
LM Studio owns the large model and memory, while the backend sends it one grounded prompt at a
time. The local HTTP boundary also lets the API report clear model-server failures instead of
crashing or loading 27 billion parameters inside every backend process.

## API contract

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Lightweight service health check. |
| `GET` | `/api/readiness` | Check PostgreSQL and the loaded local Qwen model. |
| `POST` | `/api/documents` | Upload and index one PDF. Returns a `document_id`. |
| `POST` | `/api/chat` | Ask a question scoped to a `document_id`. Returns an answer and source metadata. |

Scoping chat requests with a `document_id` is deliberate: it replaces the old process-global “last uploaded file” approach, which could mix documents between browser sessions.

## Current scope and intentional limitations

This is now a clean RAG foundation, not a finished enterprise retrieval system. It does not yet include OCR for scanned PDFs, hybrid keyword/vector search, reranking, conversational memory, ingestion queues, user accounts, automated evaluation, tracing, or production deployment.

Those are valuable next steps, but each adds a new concept. We will introduce them in a measured order so the architecture remains understandable.

## Project roadmap

The living roadmap is maintained in [PLAN.md](PLAN.md). It records completed work, the local-model
direction, the theory-first workflow, phase checklists, completion criteria, and the project
decision log.

The rule for this project remains: every new RAG technique should answer a clear question—**what
failure mode does it solve, and how will we prove that it helped?**
