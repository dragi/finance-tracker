import { clearSession, getSession, isSessionValid, refreshSession } from "../auth/cognito";

const API_URL = import.meta.env.VITE_API_URL;

async function getValidIdToken() {
  let session = getSession();
  if (isSessionValid(session)) return session.idToken;

  session = await refreshSession();
  if (!isSessionValid(session)) {
    clearSession();
    throw new Error("Session expired, please log in again");
  }
  return session.idToken;
}

export async function apiRequest(path, { method = "GET", body } = {}) {
  const idToken = await getValidIdToken();

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: idToken,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearSession();
    throw new Error("Session expired, please log in again");
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed with status ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => apiRequest(path),
  post: (path, body) => apiRequest(path, { method: "POST", body }),
  put: (path, body) => apiRequest(path, { method: "PUT", body }),
  del: (path) => apiRequest(path, { method: "DELETE" }),
};
