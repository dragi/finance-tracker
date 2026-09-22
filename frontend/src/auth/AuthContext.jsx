import { createContext, useContext, useEffect, useState } from "react";
import {
  clearSession,
  getSession,
  isSessionValid,
  login as cognitoLogin,
  refreshSession,
} from "./cognito";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => getSession());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function restore() {
      const existing = getSession();
      if (isSessionValid(existing)) {
        setSession(existing);
      } else if (existing?.refreshToken) {
        try {
          setSession(await refreshSession());
        } catch {
          clearSession();
          setSession(null);
        }
      } else {
        setSession(null);
      }
      setLoading(false);
    }
    restore();
  }, []);

  async function login(username, password) {
    const newSession = await cognitoLogin(username, password);
    setSession(newSession);
    return newSession;
  }

  function logout() {
    clearSession();
    setSession(null);
  }

  const value = {
    session,
    isAuthenticated: isSessionValid(session),
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
