# Document AI Development Plan

This is the living roadmap for turning Document AI from a clean RAG baseline into a
professional, measurable, local-first RAG application. Update this file whenever a phase
starts, an important decision changes, or a milestone is completed.

## How we will work

Every phase follows the same learning loop:

1. **Theory before coding** — identify the concept, the failure mode it addresses, the design
   choices, and the measurements that will tell us whether it helped.
2. **Small implementation** — add one understandable capability at a time instead of combining
   several unmeasured RAG techniques.
3. **Verification** — run automated tests, a manual smoke test, and the relevant RAG evaluation.
4. **Theory after coding** — explain what changed, trace the data through the implementation,
   compare the result with the previous baseline, and record what we learned.

The guiding question for every proposed feature is:

> What failure mode does this solve, and how will we prove that it helped?

## Status legend

- `[x]` Completed
- `[>]` In progress
- `[ ]` Not started
- `[~]` Revisit or improve later

## Current project snapshot

### Completed foundation

- [x] One root Git repository containing the frontend and backend.
- [x] React 19 and Vite frontend with PDF upload, question input, answer output, loading states,
      error feedback, and a responsive retrieval-evidence view.
- [x] FastAPI backend with typed API contracts and separate configuration, database, HTTP, and
      RAG boundaries.
- [x] Text-based PDF extraction with page preservation.
- [x] Text cleaning and overlapping, page-aware chunking.
- [x] Local `all-MiniLM-L6-v2` embeddings.
- [x] PostgreSQL and pgvector storage with document-scoped cosine retrieval.
- [x] Grounded generation prompt and source metadata returned to the UI.
- [x] Local Qwen generation through a loopback-only LM Studio boundary.
- [x] Reproducible PostgreSQL/pgvector startup through Docker Compose.
- [x] Isolated Python environment managed by `uv`, including `pyproject.toml`, `uv.lock`, and a
      compatibility `requirements.txt`.
- [x] Root Makefile, environment examples, Git ignore rules, and project README.
- [x] Ten backend tests, backend linting/formatting, and a successful frontend production build.

### Current limitations

- [ ] There is no automated end-to-end test covering upload, retrieval, and generation; Phase 0
      has only a successful manual end-to-end smoke test.
- [ ] There is no RAG evaluation dataset or quality baseline.
- [ ] PDF parsing, embeddings, PostgreSQL, and the live model still need broader integration-test
      coverage.
- [ ] Retrieval always returns the configured top-k chunks without a relevance threshold.
- [ ] Scanned PDFs, tables, richer document structure, and OCR are unsupported.
- [ ] There is no document library, deletion, re-indexing, conversation history, authentication,
      observability, continuous integration, or deployment workflow.

## Fixed technical direction

### Local model policy

- Generation must run locally; the finished project will not depend on hosted LLM APIs.
- The initial generator is **Qwen 3.6 27B in GGUF `Q6_K` quantization**, as reported by LM Studio.
- Development hardware is a **MacBook Pro with an M4 Max and 48 GB unified memory**.
- The current model already runs successfully on this hardware, so it is the default candidate.
- LM Studio loads the model with a 32,768-token context window, using approximately 21.43 GiB of
  unified memory after loading.
- A smaller model will be considered only if evaluation shows a worthwhile improvement in
  latency or resource use without an unacceptable loss in answer quality or faithfulness.
- The embedding model is already local and remains independent from the generation model.
- A loopback-only inference endpoint is acceptable: it is a local interface, not an external
  model service, and should bind to `127.0.0.1` unless a later deployment design requires more.

### Existing technology choices

- Keep React and Vite for the frontend.
- Keep Python and FastAPI for the API and RAG orchestration.
- Keep `uv` for isolated and reproducible Python dependency management.
- Keep PostgreSQL and pgvector while the corpus and evaluation results support that choice.
- Avoid introducing a large RAG framework until the direct implementation becomes difficult to
  maintain or a measured requirement justifies one.

## Phase 0 — Local model migration and reproducible runtime

**Goal:** Replace Gemini with the local Qwen model and establish a reliable end-to-end baseline.

### Theory before coding

- Understand the separation between the application, model runtime, model weights, tokenizer,
  quantization, context window, and inference parameters.
- Compare an in-process model with a dedicated local inference server.
- Learn how prompt length, KV cache, quantization, and generation settings affect memory,
  latency, and output quality.
- Distinguish liveness from readiness: FastAPI can be alive while PostgreSQL or Qwen is not ready.

### Implementation

- [x] Record the exact Qwen model identifier, format, context limit, and local runtime.
- [x] Confirm the runtime's local interface and bind it safely to the loopback address.
- [x] Introduce a small provider-isolated local LLM client boundary.
- [x] Replace Gemini generation calls with the local Qwen client.
- [x] Remove `google-genai`, `GOOGLE_API_KEY`, `GEMINI_MODEL`, and Gemini-specific errors and text.
- [x] Add settings for the local model name, endpoint, timeouts, and generation parameters.
- [x] Add a readiness check that reports database and local-model availability without loading the
      model repeatedly.
- [x] Restore PostgreSQL, apply the pgvector schema, and document reproducible Docker Compose
      startup.
- [x] Add mocked client tests that do not require loading the 27B model.
- [x] Run a real PDF through upload, indexing, retrieval, local generation, and source display.
- [x] Record first-token latency, generation speed, memory use, and the working context
      configuration.

### Completion criteria

- [x] The full application works without an external model API or API key.
- [x] Backend tests, linting, formatting, dependency checks, and frontend build pass.
- [x] Readiness diagnostics clearly identify a stopped database or model runtime.
- [x] The README contains accurate local setup and troubleshooting instructions.
- [x] A post-phase recap explains the local inference path from request to generated answer.

### Verification record

- LM Studio model: `qwen/qwen3.6-27b`, GGUF `Q6_K`, 27B parameters.
- Loaded context: 32,768 tokens; measured loaded memory: approximately 21.43 GiB.
- Initial short generation: approximately 1.08 seconds to first token and 18.6 tokens/second.
- Manual RAG smoke test: a generated one-page PDF was extracted, embedded, stored, retrieved, and
  answered correctly by local Qwen with a Page 1 citation.
- Smoke-test answer: the model correctly retrieved `ORBIT-742` and `November` from the PDF.

## Phase 1 — RAG evaluation foundation

**Goal:** Measure the current system before attempting retrieval improvements.

### Theory before coding

- Separate retrieval quality from generation quality.
- Learn Recall@k, Mean Reciprocal Rank, context precision, answer correctness, faithfulness,
  citation accuracy, abstention quality, latency, and resource measurements.
- Understand why a plausible answer is not evidence that retrieval worked correctly.

### Implementation

- [ ] Select a small, representative collection of text-based PDFs.
- [ ] Create approximately 30–50 questions, including direct facts, paraphrases, multi-passage
      questions, exact names or numbers, and deliberately unanswerable questions.
- [ ] Record expected answers and supporting page or chunk references.
- [ ] Define a versioned evaluation-data format that can grow with the project.
- [ ] Build a retrieval evaluation command that runs without generation where possible.
- [ ] Build an answer evaluation workflow with deterministic settings and saved results.
- [ ] Produce a baseline report for retrieval, Qwen answer quality, citation quality, latency, and
      memory use.

### Completion criteria

- [ ] Retrieval and generation can be evaluated separately.
- [ ] Baseline results are saved and reproducible.
- [ ] Future RAG changes must be compared against this baseline.
- [ ] A post-phase recap explains every metric and the initial failure patterns.

## Phase 2 — Document model and ingestion quality

**Goal:** Improve the quality, traceability, and lifecycle of content entering the RAG system.

### Theory before coding

- Learn how chunk size, overlap, tokenizer boundaries, headings, tables, and page metadata affect
  retrieval.
- Understand OCR, document parsing, idempotency, content hashes, and ingestion job states.
- Define what constitutes one document, one document version, and one retrievable chunk.

### Implementation

- [ ] Add a `documents` table with metadata, status, timestamps, and ingestion errors.
- [ ] Add content hashing and duplicate-upload handling.
- [ ] Add document deletion and safe re-indexing.
- [ ] Move from character-only chunking toward token-aware and structure-aware chunking.
- [ ] Preserve headings, sections, and richer chunk metadata.
- [ ] Add OCR for scanned PDFs with clear confidence and failure handling.
- [ ] Evaluate table extraction separately rather than flattening every table blindly.
- [ ] Split the growing RAG module into focused ingestion, embedding, retrieval, and generation
      modules when the new responsibilities justify it.
- [ ] Add parser, chunker, database, and ingestion integration tests.

### Completion criteria

- [ ] Documents have an explicit, inspectable lifecycle.
- [ ] Duplicate and failed ingestion are handled predictably.
- [ ] New chunking is measured against the Phase 1 baseline.
- [ ] Scanned-document behavior is tested and documented.

## Phase 3 — Strong retrieval

**Goal:** Retrieve more complete and precise evidence for varied question types.

### Theory before coding

- Compare dense semantic retrieval with sparse keyword retrieval.
- Learn score calibration, metadata filtering, Reciprocal Rank Fusion, reranking, query rewriting,
  multi-query retrieval, and diversity methods such as MMR.
- Understand exact versus approximate vector search and when an HNSW index is justified.

### Implementation

- [ ] Add a relevance threshold and a clear no-evidence result.
- [ ] Add PostgreSQL full-text retrieval alongside pgvector retrieval.
- [ ] Fuse sparse and dense results and measure hybrid search against both individual methods.
- [ ] Add a reranking stage for the strongest candidates.
- [ ] Evaluate query rewriting and multi-query retrieval on known baseline failures.
- [ ] Add metadata filters and later evaluate multi-document retrieval.
- [ ] Add retrieval tracing that records candidates, scores, ranks, filters, and timings.
- [ ] Introduce HNSW only when corpus size and measured latency justify approximate search.

### Completion criteria

- [ ] Retrieval improvements beat the saved baseline on agreed metrics.
- [ ] Unanswerable questions no longer receive arbitrary low-quality context.
- [ ] Every retrieval stage is inspectable and testable.
- [ ] Complexity that does not produce a measured improvement is removed or kept experimental.

## Phase 4 — Grounded generation, citations, and conversation

**Goal:** Produce answers whose claims can be traced reliably to retrieved evidence.

### Theory before coding

- Learn grounded prompting, structured output, citation attribution, answer verification,
  abstention, context compression, and conversation-aware query rewriting.
- Understand why chat history should not be inserted into retrieval without controlling topic drift.

### Implementation

- [ ] Assign stable source identifiers to retrieved chunks.
- [ ] Return structured citations tied to source identifiers rather than relying only on free-form
      page references generated by the model.
- [ ] Verify citation existence and evaluate whether cited evidence supports each claim.
- [ ] Improve abstention when evidence is absent or conflicting.
- [ ] Add response streaming after correctness is stable.
- [ ] Add conversation history and rewrite follow-up questions into standalone retrieval queries.
- [ ] Record prompt version, model version, generation parameters, timings, and token counts.
- [ ] Compare the 27B Qwen model with a smaller local model only through the saved evaluation set.

### Completion criteria

- [ ] Users can trace important claims to specific evidence.
- [ ] Citation and abstention metrics improve over the baseline.
- [ ] Conversation history improves follow-up questions without harming retrieval isolation.
- [ ] The chosen default model is supported by quality, latency, and memory evidence.

## Phase 5 — Product experience

**Goal:** Turn the retrieval pipeline into a smooth, useful document workspace.

### Theory before coding

- Define the user journey, document ownership model, conversational state, accessibility needs,
  and the difference between system status and user-facing progress.

### Implementation

- [ ] Add a document library with upload status, selection, deletion, and re-indexing.
- [ ] Add saved conversations scoped to documents or explicit document collections.
- [ ] Add a PDF viewer that can navigate to cited pages and highlight evidence where possible.
- [ ] Add clear ingestion progress and actionable failure messages.
- [ ] Improve keyboard access, screen-reader behavior, mobile layout, and visual consistency.
- [ ] Add frontend unit and interaction tests.
- [ ] Introduce authentication and per-user ownership before supporting multiple users.

### Completion criteria

- [ ] The complete workflow is understandable without developer assistance.
- [ ] Document and conversation state survives page refreshes appropriately.
- [ ] Source inspection is fast and trustworthy.
- [ ] Critical frontend journeys are covered by automated tests.

## Phase 6 — Reliability, security, and deployment

**Goal:** Make the application reproducible, observable, safe, and maintainable outside a single
development machine.

### Theory before coding

- Learn integration-test boundaries, background work, retries, idempotency, observability,
  resource isolation, access control, retention, backups, and deployment tradeoffs for local
  models.

### Implementation

- [ ] Add continuous integration for tests, linting, dependency checks, and frontend builds.
- [ ] Add API, PostgreSQL/pgvector, and end-to-end integration tests.
- [ ] Move long ingestion work to a background job system when measured request times justify it.
- [ ] Add structured logs, traces, retrieval diagnostics, latency metrics, and resource monitoring.
- [ ] Add upload validation, rate limits, quotas, authorization, and retention policies.
- [ ] Add database migrations, backups, and recovery documentation.
- [ ] Define deployment profiles for development and any future shared environment.
- [ ] Add reproducible packaging for the app and document how the local model runtime is deployed.

### Completion criteria

- [ ] A clean machine can reproduce the tested application environment.
- [ ] Failures can be diagnosed from health information, logs, traces, and metrics.
- [ ] User and document boundaries are enforced before shared use.
- [ ] Deployment and recovery procedures have been exercised, not merely written.

## Decision log

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-08-27 | Use one root Git repository for the complete project. | Frontend and backend belong to one coordinated application. |
| 2026-08-27 | Use React/Vite, FastAPI, PostgreSQL/pgvector, and local sentence-transformer embeddings. | These choices provide a clear, inspectable RAG foundation with a modern UI. |
| 2026-08-27 | Use `uv` and a project-local virtual environment. | Dependencies remain isolated and reproducible without relying on global packages. |
| 2026-09-20 | Replace hosted LLM APIs with local inference. | Local inference avoids provider quotas, enables repeated evaluation, and keeps document context on the machine. |
| 2026-09-20 | Use local Qwen 3.6 27B GGUF `Q6_K` through LM Studio as the initial generator. | The detected model runs successfully on the M4 Max with 48 GB unified memory; a smaller model will be chosen only from evaluation evidence. |
| 2026-09-20 | Use a 32,768-token loaded context instead of the model's 262,144-token maximum. | The retrieved context is intentionally small, and the lower setting preserves memory and latency headroom. |
| 2026-09-20 | Run PostgreSQL/pgvector through a pinned Docker Compose service. | A container makes the database version, extension, schema initialization, and local credentials reproducible. |

## Immediate next action

Begin **Phase 1** with a theory session on why RAG evaluation separates retrieval quality from
answer quality. Then choose a small document set and define the first versioned questions and
expected evidence before changing chunking or retrieval behavior.
