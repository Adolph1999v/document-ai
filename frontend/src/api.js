const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

// Centralize response parsing so every frontend request exposes API errors consistently.
async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${apiBaseUrl}${path}`, options);
  } catch {
    throw new Error("Could not reach the API. Make sure the FastAPI server is running.");
  }

  // Some infrastructure errors may not include JSON, so parsing has a safe fallback.
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong. Please try again.");
  }

  return data;
}

export function uploadDocument(file) {
  // Browsers send file uploads as multipart form data through FormData.
  const formData = new FormData();
  formData.append("file", file);

  return request("/api/documents", {
    method: "POST",
    body: formData,
  });
}

export function askDocumentQuestion({ documentId, question }) {
  // The document identifier keeps each question scoped to one indexed PDF.
  return request("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      document_id: documentId,
      question,
    }),
  });
}
