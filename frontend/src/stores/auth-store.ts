import { create } from "zustand";
import type { AuthUser, AuthSession } from "@/lib/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  isLoading: boolean;
  setAuth: (session: AuthSession) => void;
  clearAuth: () => void;
  setIsLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  isLoading: true,
  setAuth: (session) => {
    localStorage.setItem("docmind_refresh_token", session.refresh_token);
    set({
      accessToken: session.access_token,
      refreshToken: session.refresh_token,
      user: session.user,
    });
  },
  clearAuth: () => {
    localStorage.removeItem("docmind_refresh_token");
    set({ accessToken: null, refreshToken: null, user: null });
  },
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
