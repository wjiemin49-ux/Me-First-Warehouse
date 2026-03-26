import { useState } from "react";
import { apiRequest } from "../../api/client";
import type { AuthUser } from "../../types";

type AuthResult = {
  user: AuthUser;
};

type AuthPayload = {
  email: string;
  password: string;
};

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performAuth = async (path: string, payload: AuthPayload) => {
    setPending(true);
    setError(null);
    try {
      const data = await apiRequest<AuthResult | AuthUser>(path, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      if ("user" in data) {
        setUser(data.user);
      } else {
        setUser(data);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Authentication failed.";
      setError(message);
      throw err;
    } finally {
      setPending(false);
    }
  };

  const login = async (payload: AuthPayload) => {
    await performAuth("/api/auth/login", payload);
  };

  const register = async (payload: AuthPayload) => {
    await performAuth("/api/auth/register", payload);
  };

  const logout = async () => {
    setPending(true);
    setError(null);
    try {
      await apiRequest<null>("/api/auth/logout", {
        method: "POST"
      });
      setUser(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Logout failed.";
      setError(message);
      throw err;
    } finally {
      setPending(false);
    }
  };

  return {
    user,
    pending,
    error,
    clearError: () => setError(null),
    login,
    register,
    logout
  };
}
