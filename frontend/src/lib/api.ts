const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;
const AUTH_CHECK_TIMEOUT_MS = 5000;

// Typed fetch wrapper - the ONLY function used to talk to the backend.
// Always sends credentials so the httpOnly session cookie is included
// (per D-08 and RESEARCH.md Pitfall 5 on same-site cookies).
export async function apiFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, { ...init, credentials: "include" });
}

export interface CurrentUser {
  sub: string;
  email: string;
}

async function apiFetchWithTimeout(
  path: string,
  init: RequestInit = {},
  timeoutMs = AUTH_CHECK_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await apiFetch(path, { ...init, signal: controller.signal });
  } finally {
    window.clearTimeout(timeout);
  }
}

export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  const res = await apiFetchWithTimeout("/api/health");
  if (res.status === 401) return null;
  if (!res.ok) throw new Error(`Unexpected status ${res.status}`);
  return res.json();
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
}
