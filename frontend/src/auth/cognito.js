// Thin wrapper around Cognito's InitiateAuth API using plain fetch, since the
// user pool client only allows USER_PASSWORD_AUTH (no SRP), which keeps us
// from needing the full amazon-cognito-identity-js SDK.

const REGION = import.meta.env.VITE_COGNITO_REGION;
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID;
const COGNITO_URL = `https://cognito-idp.${REGION}.amazonaws.com/`;
const STORAGE_KEY = "expense_tracker_session";

async function cognitoRequest(target, body) {
  const res = await fetch(COGNITO_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": `AWSCognitoIdentityProviderService.${target}`,
    },
    body: JSON.stringify(body),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.message || data.__type || "Cognito request failed");
  }
  return data;
}

function saveSession(authResult) {
  const session = {
    idToken: authResult.IdToken,
    accessToken: authResult.AccessToken,
    refreshToken: authResult.RefreshToken,
    // ExpiresIn is seconds from issue time
    expiresAt: Date.now() + authResult.ExpiresIn * 1000,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  return session;
}

export function getSession() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(STORAGE_KEY);
}

export async function login(username, password) {
  const data = await cognitoRequest("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: CLIENT_ID,
    AuthParameters: {
      USERNAME: username,
      PASSWORD: password,
    },
  });
  return saveSession(data.AuthenticationResult);
}

export async function refreshSession() {
  const current = getSession();
  if (!current?.refreshToken) return null;

  const data = await cognitoRequest("InitiateAuth", {
    AuthFlow: "REFRESH_TOKEN_AUTH",
    ClientId: CLIENT_ID,
    AuthParameters: {
      REFRESH_TOKEN: current.refreshToken,
    },
  });

  // refresh responses don't include a new refresh token, keep the old one
  return saveSession({
    ...data.AuthenticationResult,
    RefreshToken: current.refreshToken,
  });
}

export function isSessionValid(session) {
  return Boolean(session?.idToken) && session.expiresAt > Date.now();
}
