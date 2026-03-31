
# Frontend Spec: State Management

Files: `frontend/src/stores/workspace-store.ts` · `frontend/src/hooks/` · `frontend/src/lib/query-client.ts`

See also: [[projects/docmind-vlm/specs/frontend/components]] · [[projects/docmind-vlm/specs/frontend/api-client]]

---

## State Philosophy

DocMind-VLM uses a **dual state management** approach:
- **React Query (@tanstack/react-query)** — All server state (documents, extractions, chat history, templates)
- **Zustand** — Local UI state (active tab, overlay mode, zoom level, selected field)

**Do NOT use**: Redux, Jotai, Context API for server state, `useState` for server-fetched data.
**DO use**: React Query for anything fetched from API. Zustand for UI-only ephemeral state. `useState` for component-local state (form inputs, toggles).

---

## React Query Setup

```typescript
/**
 * src/lib/query-client.ts
 *
 * Central React Query client configuration.
 * Imported by App.tsx and wrapped in QueryClientProvider.
 */

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,          // 30s — document data doesn't change often
      retry: 1,                   // Retry once on failure, then show error
      refetchOnWindowFocus: false, // Don't refetch when user tabs back
    },
    mutations: {
      retry: 0,                   // Don't retry mutations — let user decide
    },
  },
});
```

**QueryClientProvider in App.tsx:**

```typescript
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/query-client";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* Router and layout */}
    </QueryClientProvider>
  );
}
```

---

## Query Hooks (`src/hooks/`)

### `useDocuments.ts` — Document list with pagination

```typescript
/**
 * src/hooks/useDocuments.ts
 *
 * Fetches paginated document list for the dashboard.
 * Invalidated after upload or delete.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchDocuments,
  createDocument,
  deleteDocument,
} from "@/lib/api";
import type { DocumentCreate } from "@/types/api";

export function useDocuments(page = 1, limit = 20) {
  return useQuery({
    queryKey: ["documents", page, limit],
    queryFn: () => fetchDocuments(page, limit),
  });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DocumentCreate) => createDocument(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });
}
```

### `useExtraction.ts` — Extraction results for a document

```typescript
/**
 * src/hooks/useExtraction.ts
 *
 * Fetches extraction results, audit trail, overlay data, and comparison
 * for a specific document. Only fetches when documentId is provided.
 */

import { useQuery } from "@tanstack/react-query";
import {
  fetchExtraction,
  fetchAuditTrail,
  fetchOverlay,
  fetchComparison,
} from "@/lib/api";

export function useExtraction(documentId: string) {
  return useQuery({
    queryKey: ["extraction", documentId],
    queryFn: () => fetchExtraction(documentId),
    enabled: !!documentId,
  });
}

export function useAuditTrail(documentId: string) {
  return useQuery({
    queryKey: ["audit-trail", documentId],
    queryFn: () => fetchAuditTrail(documentId),
    enabled: !!documentId,
  });
}

export function useOverlay(documentId: string) {
  return useQuery({
    queryKey: ["overlay", documentId],
    queryFn: () => fetchOverlay(documentId),
    enabled: !!documentId,
  });
}

export function useComparison(documentId: string) {
  return useQuery({
    queryKey: ["comparison", documentId],
    queryFn: () => fetchComparison(documentId),
    enabled: !!documentId,
  });
}
```

### `useChat.ts` — Chat history + message sending

```typescript
/**
 * src/hooks/useChat.ts
 *
 * Chat history query and message mutation.
 * Chat messages use SSE streaming (handled in ChatPanel component),
 * but history is fetched via standard REST.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchChatHistory } from "@/lib/api";
import type { ChatHistoryResponse } from "@/types/api";

export function useChatHistory(documentId: string, page = 1, limit = 50) {
  return useQuery<ChatHistoryResponse>({
    queryKey: ["chat-history", documentId, page, limit],
    queryFn: () => fetchChatHistory(documentId, page, limit),
    enabled: !!documentId,
  });
}

/**
 * Hook to invalidate chat history after a new message is sent.
 * Called from ChatPanel after SSE stream completes.
 */
export function useInvalidateChatHistory(documentId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["chat-history", documentId] });
  };
}
```

### `useTemplates.ts` — Template list and detail

```typescript
/**
 * src/hooks/useTemplates.ts
 *
 * Fetches available extraction templates.
 * Templates are relatively static — use longer staleTime.
 */

import { useQuery } from "@tanstack/react-query";
import { fetchTemplates, fetchTemplate } from "@/lib/api";

export function useTemplates() {
  return useQuery({
    queryKey: ["templates"],
    queryFn: fetchTemplates,
    staleTime: 5 * 60_000, // 5 minutes — templates rarely change
  });
}

export function useTemplate(type: string) {
  return useQuery({
    queryKey: ["template", type],
    queryFn: () => fetchTemplate(type),
    enabled: !!type,
    staleTime: 5 * 60_000,
  });
}
```

---

## Zustand Store (`src/stores/`)

### `workspace-store.ts` — UI state for the document workspace

```typescript
/**
 * src/stores/workspace-store.ts
 *
 * Local UI state for the WorkspacePage.
 * No persistence — resets when navigating away.
 * All server data comes from React Query hooks.
 */

import { create } from "zustand";

interface WorkspaceState {
  // Active sidebar tab
  activeTab: "extraction" | "chat" | "audit" | "compare";

  // Document viewer overlay mode
  overlayMode: "none" | "confidence" | "bounding_box";

  // Selected field (synced between ExtractionPanel and DocumentViewer)
  selectedFieldId: string | null;

  // Zoom level for DocumentViewer
  zoomLevel: number;

  // Processing state
  isProcessing: boolean;

  // Actions
  setActiveTab: (tab: WorkspaceState["activeTab"]) => void;
  setOverlayMode: (mode: WorkspaceState["overlayMode"]) => void;
  selectField: (fieldId: string | null) => void;
  setZoomLevel: (level: number) => void;
  setIsProcessing: (processing: boolean) => void;
  resetWorkspace: () => void;
}

const INITIAL_STATE = {
  activeTab: "extraction" as const,
  overlayMode: "none" as const,
  selectedFieldId: null,
  zoomLevel: 1.0,
  isProcessing: false,
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  ...INITIAL_STATE,

  setActiveTab: (tab) => set({ activeTab: tab }),
  setOverlayMode: (mode) => set({ overlayMode: mode }),
  selectField: (fieldId) => set({ selectedFieldId: fieldId }),
  setZoomLevel: (level) => set({ zoomLevel: Math.max(0.25, Math.min(5.0, level)) }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  resetWorkspace: () => set(INITIAL_STATE),
}));
```

### `auth-store.ts` — Auth state (no Supabase dependency)

```typescript
/**
 * src/stores/auth-store.ts
 *
 * Stores JWT tokens and user info from backend auth endpoints.
 * Initialized in App.tsx via refresh token recovery from localStorage.
 * No Supabase types — uses custom AuthUser/AuthSession from lib/auth.ts.
 */

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
```

**Token strategy:**
- `accessToken` — memory only (never localStorage)
- `refreshToken` — persisted in localStorage for session recovery across page reloads
- On mount: if refresh token in localStorage → call backend `/auth/refresh` → populate store

---

## State Update Rules

### Always clear stale state before new queries

```typescript
// CORRECT: Reset workspace when switching documents
useEffect(() => {
  useWorkspaceStore.getState().resetWorkspace();
}, [documentId]);

// WRONG: Stale selectedFieldId from previous document persists
```

### Use React Query's `enabled` for conditional fetching

```typescript
// CORRECT: Only fetch extraction when documentId is available
useQuery({
  queryKey: ["extraction", documentId],
  queryFn: () => fetchExtraction(documentId),
  enabled: !!documentId,  // won't fire until documentId is set
});

// WRONG: Fetch unconditionally and handle empty string in API
useQuery({
  queryKey: ["extraction", documentId],
  queryFn: () => fetchExtraction(documentId), // fires with ""
});
```

### Never store derived state

```typescript
// CORRECT: Derive from query data
const highConfidenceFields = extraction?.fields.filter((f) => f.confidence >= 0.8) ?? [];

// WRONG: Store derived data in Zustand
const [highConfidenceFields, setHighConfidenceFields] = useState([]);
useEffect(() => {
  setHighConfidenceFields(extraction?.fields.filter(...));
}, [extraction]);
```

### Zustand for UI-only state that doesn't need persistence

```typescript
// CORRECT: Overlay mode is ephemeral UI state
const overlayMode = useWorkspaceStore((s) => s.overlayMode);

// WRONG: Storing API response data in Zustand
const [extraction, setExtraction] = useWorkspaceStore((s) => s.extraction);
```

### Never mutate state — always create new objects

```typescript
// CORRECT: Immutable update
setMessages((prev) => [...prev, newMessage]);

// WRONG: Mutation
setMessages((prev) => {
  prev.push(newMessage);  // mutates!
  return prev;
});
```

---

## Derived State

Prefer deriving values instead of storing them separately:

```typescript
// CORRECT: Derive field count from extraction
const fieldCount = extraction?.fields.length ?? 0;
// Recomputed on every render (cheap)

// WRONG: Store derived state separately
const [fieldCount, setFieldCount] = useState(0);
// Now you need to keep it in sync manually
```

---

## Loading/Error Patterns

### React Query handles loading/error automatically

```typescript
function ExtractionView({ documentId }: { documentId: string }) {
  const { data: extraction, isLoading, error } = useExtraction(documentId);

  if (isLoading) {
    return <ExtractionSkeleton />;
  }

  if (error) {
    return (
      <div className="text-sm text-destructive">
        {error instanceof ApiError
          ? `Error (${error.statusCode}): ${error.detail}`
          : "Failed to load extraction data."}
      </div>
    );
  }

  return <ExtractionPanel extraction={extraction} ... />;
}
```

### Skeleton components during loading

```typescript
// Show shimmer/skeleton while data loads
// Use shadcn Skeleton component or simple div placeholders
function ExtractionSkeleton() {
  return (
    <div className="flex flex-col gap-2 animate-pulse">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="h-8 bg-muted rounded" />
      ))}
    </div>
  );
}
```

### Error boundaries for component-level failures

```typescript
// Wrap workspace panels in error boundaries
// so one panel crash doesn't take down the entire workspace
<ErrorBoundary fallback={<PanelError />}>
  <ExtractionPanel ... />
</ErrorBoundary>
```

---

## Component -> State Flow

```
User navigates to /workspace/:documentId
    |
AuthGuard checks session (auth-store)
    |
WorkspacePage mounts
    |
    +-- useExtraction(documentId)     <- React Query fetches extraction
    +-- useWorkspaceStore()           <- Zustand provides UI state
    |
User clicks field in ExtractionPanel
    |
onFieldSelect(fieldId)
    |
useWorkspaceStore.selectField(fieldId)
    |
DocumentViewer reads selectedFieldId -> highlights overlay
    |
User changes overlay mode
    |
useWorkspaceStore.setOverlayMode("confidence")
    |
DocumentViewer reads overlayMode -> renders color-coded overlays
    |
User sends chat message
    |
ChatPanel creates SSE stream (lib/api.ts)
    |
Tokens stream in -> local state in ChatPanel
    |
Stream complete -> invalidate chat-history query
    |
Re-render -> updated message list
```

---

## TypeScript State Types

All state types come from `@/types/api.ts` — never define inline types for state:

```typescript
// CORRECT: Import from types/api.ts
import type { ExtractionResponse, ChatMessageResponse } from "@/types/api";
const { data } = useQuery<ExtractionResponse>({ ... });

// WRONG: Don't define inline
const { data } = useQuery<{ fields: { id: string; value: string }[] }>({ ... });
```

See [[projects/docmind-vlm/specs/frontend/api-client]] for type definitions.

---

## Query Key Convention

All query keys follow a consistent pattern for predictable invalidation:

| Hook | Query Key | Invalidated By |
|------|-----------|---------------|
| `useDocuments` | `["documents", page, limit]` | Upload, delete |
| `useExtraction` | `["extraction", documentId]` | Processing complete |
| `useAuditTrail` | `["audit-trail", documentId]` | Processing complete |
| `useOverlay` | `["overlay", documentId]` | Processing complete |
| `useComparison` | `["comparison", documentId]` | Processing complete |
| `useChatHistory` | `["chat-history", documentId, page, limit]` | Chat message sent |
| `useTemplates` | `["templates"]` | Rarely (admin action) |
| `useTemplate` | `["template", type]` | Rarely (admin action) |

**Invalidation after processing completes:**

```typescript
// In WorkspacePage, after ProcessingProgress.onComplete fires:
const queryClient = useQueryClient();

const handleProcessingComplete = () => {
  useWorkspaceStore.getState().setIsProcessing(false);
  queryClient.invalidateQueries({ queryKey: ["extraction", documentId] });
  queryClient.invalidateQueries({ queryKey: ["audit-trail", documentId] });
  queryClient.invalidateQueries({ queryKey: ["overlay", documentId] });
  queryClient.invalidateQueries({ queryKey: ["comparison", documentId] });
};
```
