import { useRef, useState } from "react";

import { askDocumentQuestion, uploadDocument } from "./api";
import "./App.css";

const MAX_FILE_SIZE_MB = 20;

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isPdf(file) {
  return file?.type === "application/pdf" || file?.name.toLowerCase().endsWith(".pdf");
}

function App() {
  const fileInputRef = useRef(null);

  // Document, conversation, and feedback state are kept separate so each UI
  // section can reflect its own stage of the upload-and-question workflow.
  const [selectedFile, setSelectedFile] = useState(null);
  const [document, setDocument] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [uploadState, setUploadState] = useState("idle");
  const [chatState, setChatState] = useState("idle");
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // Choosing a replacement file clears results tied to the previously indexed PDF.
  const chooseFile = (file) => {
    if (!file) {
      return;
    }

    if (!isPdf(file)) {
      setError("Please choose a PDF file.");
      return;
    }

    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`Please choose a PDF smaller than ${MAX_FILE_SIZE_MB} MB.`);
      return;
    }

    setSelectedFile(file);
    setDocument(null);
    setAnswer("");
    setSources([]);
    setQuestion("");
    setError("");
  };

  const handleFileChange = (event) => {
    chooseFile(event.target.files?.[0]);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    chooseFile(event.dataTransfer.files?.[0]);
  };

  // Uploading also performs backend extraction, chunking, embedding, and storage.
  const handleUpload = async () => {
    if (!selectedFile || uploadState === "uploading") {
      return;
    }

    setUploadState("uploading");
    setError("");

    try {
      const uploadedDocument = await uploadDocument(selectedFile);
      setDocument(uploadedDocument);
      setAnswer("");
      setSources([]);
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setUploadState("idle");
    }
  };

  // Questions are submitted only after the backend returns a document identifier.
  const handleQuestionSubmit = async (event) => {
    event.preventDefault();

    const trimmedQuestion = question.trim();
    if (!document || !trimmedQuestion || chatState === "loading") {
      return;
    }

    setChatState("loading");
    setError("");

    try {
      const result = await askDocumentQuestion({
        documentId: document.document_id,
        question: trimmedQuestion,
      });
      setAnswer(result.answer);
      setSources(result.sources);
    } catch (chatError) {
      setError(chatError.message);
    } finally {
      setChatState("idle");
    }
  };

  const openFilePicker = () => fileInputRef.current?.click();

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="/" aria-label="Document AI home">
          <span className="brand-mark" aria-hidden="true">DA</span>
          <span>Document AI</span>
        </a>
        <span className="build-label">RAG learning lab</span>
      </header>

      <main className="page-content">
        <section className="hero" aria-labelledby="page-title">
          <p className="eyebrow">Grounded answers from your documents</p>
          <h1 id="page-title">Ask better questions of your PDFs.</h1>
          <p className="hero-copy">
            Upload a text-based PDF, then explore it through retrieval-augmented
            answers with page-level source context.
          </p>
        </section>

        <div className="workspace-grid">
          <section className="panel upload-panel" aria-labelledby="upload-title">
            <div className="panel-heading">
              <div>
                <p className="step-label">01 — Index</p>
                <h2 id="upload-title">Add a document</h2>
              </div>
              {document && <span className="status-badge success">Ready</span>}
            </div>

            <input
              ref={fileInputRef}
              className="visually-hidden"
              id="pdf-upload"
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
            />

            <button
              className={`dropzone ${isDragging ? "is-dragging" : ""}`}
              type="button"
              onClick={openFilePicker}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <span className="file-glyph" aria-hidden="true">PDF</span>
              <strong>{selectedFile ? selectedFile.name : "Drop a PDF here"}</strong>
              <span>
                {selectedFile
                  ? `${formatFileSize(selectedFile.size)} · Click to replace`
                  : `or click to browse · up to ${MAX_FILE_SIZE_MB} MB`}
              </span>
            </button>

            <button
              className="primary-button"
              type="button"
              onClick={handleUpload}
              disabled={!selectedFile || uploadState === "uploading"}
            >
              {uploadState === "uploading" ? "Indexing document…" : "Index document"}
            </button>

            <div className="ingestion-note">
              <span aria-hidden="true">↗</span>
              <p>
                Text is extracted page by page, split into overlapping chunks, and
                stored as semantic vectors for retrieval.
              </p>
            </div>

            {document && (
              <div className="document-summary" aria-live="polite">
                <div>
                  <span className="document-summary-label">Indexed document</span>
                  <strong>{document.filename}</strong>
                </div>
                <span>{document.chunks_stored} chunks</span>
              </div>
            )}
          </section>

          <section className="panel chat-panel" aria-labelledby="chat-title">
            <div className="panel-heading">
              <div>
                <p className="step-label">02 — Retrieve &amp; answer</p>
                <h2 id="chat-title">Ask a question</h2>
              </div>
              <span className={`status-badge ${document ? "success" : "muted"}`}>
                {document ? "Document selected" : "Waiting for PDF"}
              </span>
            </div>

            <form className="question-form" onSubmit={handleQuestionSubmit}>
              <label htmlFor="question">Your question</label>
              <textarea
                id="question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={
                  document
                    ? "For example, what are the key recommendations?"
                    : "Upload and index a PDF to begin asking questions."
                }
                disabled={!document || chatState === "loading"}
                rows="4"
              />
              <div className="question-actions">
                <span>{document ? "Answers are constrained to retrieved context." : ""}</span>
                <button
                  className="secondary-button"
                  type="submit"
                  disabled={!document || !question.trim() || chatState === "loading"}
                >
                  {chatState === "loading" ? "Finding evidence…" : "Ask document"}
                </button>
              </div>
            </form>

            <div className="answer-area" aria-live="polite">
              {chatState === "loading" && (
                <div className="answer-placeholder loading-state">
                  <span className="loading-dot" aria-hidden="true" />
                  Retrieving relevant passages and preparing an answer…
                </div>
              )}

              {chatState !== "loading" && answer && (
                <article className="answer-card">
                  <p className="answer-label">Grounded answer</p>
                  <p>{answer}</p>
                </article>
              )}

              {chatState !== "loading" && !answer && (
                <div className="answer-placeholder">
                  {document
                    ? "Your grounded answer will appear here."
                    : "Your answer space is ready when your document is indexed."}
                </div>
              )}
            </div>
          </section>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <strong>Something needs attention.</strong> {error}
          </div>
        )}

        {sources.length > 0 && (
          <section className="sources-section" aria-labelledby="sources-title">
            <div className="sources-heading">
              <div>
                <p className="eyebrow">Retrieval trace</p>
                <h2 id="sources-title">Evidence used for this answer</h2>
              </div>
              <p>These are the passages selected before the model generated its response.</p>
            </div>
            <div className="sources-grid">
              {sources.map((source) => (
                <article
                  className="source-card"
                  key={`${source.page_number}-${source.chunk_index}`}
                >
                  <div className="source-meta">
                    <span>Page {source.page_number}</span>
                    <span>{Math.round(source.similarity_score * 100)}% similarity</span>
                  </div>
                  <p>{source.excerpt}</p>
                </article>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
