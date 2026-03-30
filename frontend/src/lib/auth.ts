/**
 * Auth client — calls backend /api/v1/auth/* endpoints.
 * No Supabase JS dependency.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8009";

export interface AuthUser {
  id: string;
  email: string;
  created_at: string | null;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  token_type: string;
  user: AuthUser;
}

async function authFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}/api/v1/auth${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    },
  });

  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      message = body.message ?? body.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string): Promise<AuthSession> {
  return authFetch<AuthSession>("/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function signup(email: string, password: string): Promise<AuthSession> {
  return authFetch<AuthSession>("/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(accessToken: string): Promise<void> {
  await authFetch<void>("/logout", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}

export async function refreshSession(refreshToken: string): Promise<AuthSession> {
  return authFetch<AuthSession>("/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function getSession(accessToken: string): Promise<{ user: AuthUser }> {
  return authFetch<{ user: AuthUser }>("/session", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
