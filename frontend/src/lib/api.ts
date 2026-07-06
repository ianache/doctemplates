const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

// Typed fetch wrapper — the ONLY function used to talk to the backend.
// Always sends credentials so the httpOnly session cookie is included
// (per D-08 and RESEARCH.md Pitfall 5 on same-site cookies).
export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, { ...init, credentials: "include" });
}
