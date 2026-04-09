# Issue #26: Auth UI — Supabase OAuth, AuthGuard, Session Management

## Summary

Implement the authentication UI layer: Supabase OAuth login with Google and GitHub buttons, an AuthGuard component that wraps protected routes and redirects unauthenticated users, session management via the Zustand auth-store, a login page, a logout button in the dashboard header, and proper redirect-after-login flow. The auth-store already exists as a scaffold; this issue wires it to real Supabase auth events and integrates it into the router.

## Context

- **Phase**: 6 — Frontend
- **Priority**: P0
- **Labels**: `phase-6-frontend`, `frontend`, `tdd`
- **Dependencies**: #25 (landing page CTA buttons link to auth)
- **Branch**: `feat/26-auth-ui`
- **Estimated scope**: M

## Specs to Read

- `specs/frontend/components.md` — AuthGuard component spec with full code
- `specs/frontend/state.md` — auth-store spec, session initialization in App.tsx
- `specs/frontend/api-client.md` — supabase.ts auth helpers (signInWithGoogle, signInWithGitHub, signOut)
- `specs/conventions/security.md` — Supabase JWT auth flow
- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 1.1 through AC 1.5

## Current State (Scaffold)

**File: `frontend/src/components/workspace/AuthGuard.tsx`**
```typescript
export function AuthGuard() {
  return <div>AuthGuard</div>;
}
```

**File: `frontend/src/stores/auth-store.ts`** (already implemented):
```typescript
import { create } from "zustand";
import type { Session, User } from "@supabase/supabase-js";

interface AuthState {
  session: Session | null;
  user: User | null;
  isLoading: boolean;
  setSession: (session: Session | null) => void;
  setIsLoading: (loading: boolean) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  session: null,
  user: null,
  isLoading: true,
  setSession: (session) => set({ session, user: session?.user ?? null }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
```

**File: `frontend/src/lib/supabase.ts`** (already implemented):
```typescript
export async function signInWithGoogle() {
  return supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${window.location.origin}/dashboard` },
  });
}

export async function signInWithGitHub() {
  return supabase.auth.signInWithOAuth({
    provider: "github",
    options: { redirectTo: `${window.location.origin}/dashboard` },
  });
}

export async function signOut() {
  return supabase.auth.signOut();
}
```

**File: `frontend/src/App.tsx`** (routes exist but no AuthGuard wrapping):
```typescript
export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/workspace/:documentId" element={<Workspace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

**Missing files:**
- `frontend/src/pages/LoginPage.tsx` — dedicated login page (optional, CTA may redirect directly)

## Requirements

### Functional

1. **AuthGuard**: Wrapper component that checks Supabase session. If no session, redirects to `/` (landing). Shows loading spinner while checking. Wraps `/dashboard` and `/workspace/:documentId` routes.
2. **Auth Initialization**: On App mount, subscribe to `supabase.auth.onAuthStateChange` and sync session to `useAuthStore.setSession()`. Set `isLoading: false` after initial check.
3. **Login Flow**: Landing page CTA buttons call `signInWithGoogle()` or `signInWithGitHub()`. After OAuth redirect, Supabase sets session cookie and redirects to `/dashboard`.
4. **Logout**: Button in dashboard header calls `signOut()`, clears auth-store, redirects to `/`.
5. **Session Persistence**: Sessions persist across browser restarts via Supabase refresh token flow (handled by Supabase JS client automatically).
6. **User Display**: Show user email or avatar in dashboard header from `useAuthStore((s) => s.user)`.

### Non-Functional

- Auth check completes in < 500ms (spinner shown during check)
- No flash of protected content before redirect
- Supabase environment variables validated at startup (fail fast)

## Implementation Plan

### AuthGuard Component

**`frontend/src/components/workspace/AuthGuard.tsx`**:
```typescript
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { Loader2 } from "lucide-react";
import type { Session } from "@supabase/supabase-js";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setIsLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => { setSession(s); },
    );

    return () => { subscription.unsubscribe(); };
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
```

### App.tsx Auth Initialization

**`frontend/src/App.tsx`** (updated):
```typescript
import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/query-client";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/stores/auth-store";
import { AuthGuard } from "@/components/workspace/AuthGuard";
import { LandingPage } from "@/pages/LandingPage";
import { Dashboard } from "@/pages/Dashboard";
import { Workspace } from "@/pages/Workspace";

export function App() {
  const setSession = useAuthStore((s) => s.setSession);
  const setIsLoading = useAuthStore((s) => s.setIsLoading);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setIsLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => { setSession(session); },
    );

    return () => { subscription.unsubscribe(); };
  }, [setSession, setIsLoading]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard" element={<AuthGuard><Dashboard /></AuthGuard>} />
          <Route path="/workspace/:documentId" element={<AuthGuard><Workspace /></AuthGuard>} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

### Dashboard Header with User Info + Logout

```typescript
// Inside Dashboard page header area
import { useAuthStore } from "@/stores/auth-store";
import { signOut } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";

function DashboardHeader() {
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const handleLogout = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <header className="flex items-center justify-between p-4 border-b">
      <span className="text-lg font-bold">DocMind-VLM</span>
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">{user?.email}</span>
        <Button variant="ghost" size="icon" onClick={handleLogout}>
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
```

### Supabase OAuth Flow Diagram

```
User clicks "Try it Free — Google" on Landing Page
  → signInWithGoogle() called
  → Supabase redirects to Google OAuth consent screen
  → User approves
  → Google redirects to Supabase callback URL
  → Supabase sets session (access_token + refresh_token)
  → Supabase redirects to `window.location.origin/dashboard`
  → App.tsx onAuthStateChange fires → auth-store updated
  → AuthGuard sees session → renders Dashboard
```

## Acceptance Criteria

- [ ] Google OAuth login works and redirects to dashboard — AC 1.1
- [ ] GitHub OAuth login works and redirects to dashboard — AC 1.2
- [ ] Unauthenticated users accessing `/dashboard` or `/workspace/:id` are redirected to `/` — AC 1.3
- [ ] Session persists across browser restarts — AC 1.5
- [ ] Auth-store is initialized on App mount via `onAuthStateChange`
- [ ] Loading spinner shown while checking auth (no flash of protected content)
- [ ] Logout button in dashboard header clears session and redirects to `/`
- [ ] User email displayed in dashboard header
- [ ] AuthGuard accepts `children` prop with proper TypeScript interface
- [ ] No hardcoded Supabase credentials in source code

## Files Changed

- `frontend/src/components/workspace/AuthGuard.tsx` — implement from stub
- `frontend/src/App.tsx` — add auth initialization + wrap routes with AuthGuard
- `frontend/src/pages/Dashboard.tsx` — add header with user info and logout
- `frontend/src/stores/auth-store.ts` — no changes needed (already correct)
- `frontend/src/lib/supabase.ts` — no changes needed (already correct)

## Verification

```bash
cd frontend
npm run typecheck           # No TypeScript errors
npm run lint                # No lint errors
npm run dev                 # Manual testing:
# 1. Visit /dashboard directly → should redirect to /
# 2. Click "Try it Free — Google" → OAuth flow → lands on /dashboard
# 3. Refresh browser → still on /dashboard (session persists)
# 4. Click logout → redirected to /
# 5. Visit /workspace/any-id → redirected to /
```
