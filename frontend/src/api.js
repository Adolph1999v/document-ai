const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${apiBaseUrl}${path}`, options);
  } catch {
    throw new Error("Could not reach the API. Make sure the FastAPI server is running.");
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Something went wrong. Please try again.");
  }

  return data;
}

export function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);

  return request("/api/documents", {
    method: "POST",
    body: formData,
  });
}

export function askDocumentQuestion({ documentId, question }) {
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
