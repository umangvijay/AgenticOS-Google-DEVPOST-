"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

// ── Types ────────────────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string;
  auth_provider: string;
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
  loginAsGuest: () => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<string | null>;
  updateProfile: (data: { name?: string; avatar_url?: string }) => Promise<void>;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ── Context ──────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

// ── Provider ─────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    isLoading: true,
    isAuthenticated: false,
  });

  // Load tokens from localStorage on mount
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
        setState(s => ({ ...s, isLoading: false }));
      }
    } else {
      setState(s => ({ ...s, isLoading: false }));
    }
  }, []);

  // Persist auth state
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

  // ── API Methods ────────────────────────────────────────────────

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Login failed");
    }
    const data = await res.json();
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const signup = useCallback(async (email: string, password: string, name: string) => {
    const res = await fetch(`${API_BASE}/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Signup failed");
    }
    const data = await res.json();
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const loginWithGoogle = useCallback(async (idToken?: string, code?: string) => {
    const body: Record<string, string> = {};
    if (idToken) body.id_token = idToken;
    if (code) body.code = code;

    const res = await fetch(`${API_BASE}/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Google login failed");
    }
    const data = await res.json();
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const loginAsGuest = useCallback(async () => {
    const res = await fetch(`${API_BASE}/auth/guest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Guest login failed");
    }
    const data = await res.json();
    persistAuth(data.user, data.access_token, data.refresh_token);
  }, [persistAuth]);

  const logout = useCallback(async () => {
    if (state.accessToken) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${state.accessToken}` },
        });
      } catch {
        // Logout locally even if server fails
      }
    }
    clearAuth();
  }, [state.accessToken, clearAuth]);

  const refreshAccessToken = useCallback(async (): Promise<string | null> => {
    if (!state.refreshToken) return null;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: state.refreshToken }),
      });

      if (!res.ok) {
        clearAuth();
        return null;
      }

      const data = await res.json();
      persistAuth(data.user, data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      clearAuth();
      return null;
    }
  }, [state.refreshToken, persistAuth, clearAuth]);

  const updateProfile = useCallback(async (updates: { name?: string; avatar_url?: string }) => {
    const res = await fetch(`${API_BASE}/auth/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${state.accessToken}`,
      },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error("Profile update failed");
    const user = await res.json();
    setState(s => ({
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
