"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import {
  type AuthUser,
  getToken,
  logout as clearAuth,
  setUser as storeUser,
} from "@/lib/auth";
import { fetchCurrentUser, loginApi, registerApi } from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // On mount: validate token by calling /auth/me (with 5s timeout)
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    // Timeout: if backend doesn't respond in 5s, treat as unauthenticated
    const timeout = setTimeout(() => {
      clearAuth();
      setUser(null);
      setIsLoading(false);
    }, 5000);

    fetchCurrentUser()
      .then((u) => {
        clearTimeout(timeout);
        setUser(u);
        storeUser(u);
      })
      .catch(() => {
        clearTimeout(timeout);
        clearAuth();
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await loginApi(email, password);
    setUser(data.user);
  }, []);

  const register = useCallback(
    async (email: string, password: string, name: string) => {
      const data = await registerApi(email, password, name);
      setUser(data.user);
    },
    [],
  );

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: !!user,
      isLoading,
      login,
      register,
      logout,
    }),
    [user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
