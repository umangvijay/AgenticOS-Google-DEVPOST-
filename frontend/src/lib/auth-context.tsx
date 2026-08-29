"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

export interface User {
  id: string;
  email: string;
  auth_provider: string;
  name: string;
  avatar_url?: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, name: string) => Promise<void>;
  loginWithGoogle: (idToken?: string, code?: string) => Promise<void>;
  loginAsGuest: (signal?: AbortSignal) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<string | null>;
  updateProfile: (data: { name?: string; avatar_url?: string }) => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

function parseApiError(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;
  const detail = (data as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) return String((item as { msg: unknown }).msg);
      return "";
    }).filter(Boolean);
    return parts.join(". ") || fallback;
  }
  return fallback;
}

async function fetchJson(url: string, init: RequestInit, timeoutMs: number) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const parent = init.signal;
  if (parent) {
    if (parent.aborted) controller.abort();
    else parent.addEventListener("abort", () => controller.abort(), { once: true });
  }
  try {
    const res = await fetch(url, { ...init, signal: controller.signal });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(parseApiError(data, `Request failed (${res.status})`));
    }
    return data;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("The request timed out. Check that the API is running, then try again.");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    isLoading: true,
    isAuthenticated: false,
  });

  useEffect(() => {
    const stored = localStorage.getItem("agentos_auth");
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        setState({
          user: parsed.user,
          accessToken: parsed.accessToken,
          refreshToken: parsed.refreshToken,
          isLoading: false,
          isAuthenticated: !!parsed.accessToken,
        });
      } catch {
        localStorage.removeItem("agentos_auth");
        setState((s) => ({ ...s, isLoading: false }));
      }
    } else {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  const persistAuth = useCallback((user: User, accessToken: string, refreshToken: string) => {
    const data = { user, accessToken, refreshToken };
    localStorage.setItem("agentos_auth", JSON.stringify(data));
    setState({
      user,
      accessToken,
      refreshToken,
      isLoading: false,
      isAuthenticated: true,
    });
  }, []);

  const clearAuth = useCallback(() => {
    localStorage.removeItem("agentos_auth");
    setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isLoading: false,
      isAuthenticated: false,
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await fetchJson(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    }, 12000);
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const signup = useCallback(async (email: string, password: string, name: string) => {
    const data = await fetchJson(`${API_BASE}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password, name }),
    }, 15000);
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const loginWithGoogle = useCallback(async (idToken?: string, code?: string) => {
    const body: Record<string, string> = {};
    if (idToken) body.id_token = idToken;
    if (code) body.code = code;

    const data = await fetchJson(`${API_BASE}/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    }, 15000);
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const loginAsGuest = useCallback(async (signal?: AbortSignal) => {
    const data = await fetchJson(`${API_BASE}/auth/guest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      signal,
    }, 8000);
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const logout = useCallback(async () => {
    if (state.accessToken) {
      try {
        await fetchJson(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${state.accessToken}` },
          credentials: "include",
        }, 5000);
      } catch {
        // Logout locally even if server fails
      }
    }
    clearAuth();
  }, [state.accessToken, clearAuth]);

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    if (!state.refreshToken) return null;

    try {
      const data = await fetchJson(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ refresh_token: state.refreshToken }),
      }, 8000);
      persistAuth(data.user, data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      clearAuth();
      return null;
    }
  }, [state.refreshToken, persistAuth, clearAuth]);

  const updateProfile = useCallback(async (updates: { name?: string; avatar_url?: string }) => {
    const user = await fetchJson(`${API_BASE}/auth/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.accessToken}`,
      },
      credentials: "include",
      body: JSON.stringify(updates),
    }, 8000);
    setState((s) => ({
      ...s,
      user: { ...s.user!, ...user },
    }));
  }, [state.accessToken]);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        signup,
        loginWithGoogle,
        loginAsGuest,
        logout,
        refreshAccessToken,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
