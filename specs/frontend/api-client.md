# Frontend Spec: API Client

Files: `frontend/src/lib/auth.ts` · `frontend/src/lib/api.ts` · `frontend/src/types/api.ts`

See also: [[projects/docmind-vlm/specs/frontend/components]] · [[projects/docmind-vlm/specs/frontend/state]]

---

## Structure

```
frontend/src/
├── lib/
│   ├── auth.ts        <- Auth client (calls backend /api/v1/auth/*)
│   ├── api.ts         <- Backend API calls (fetch wrapper with JWT from auth store)
│   └── utils.ts       <- Shared utilities
└── types/
    └── api.ts         <- TypeScript interfaces mirroring backend API
```

**Rule**: Types and API functions are in separate files.
- `types/api.ts` — pure TypeScript interfaces, no logic
- `lib/api.ts` — fetch calls, error handling, URL construction
- `lib/auth.ts` — login, signup, logout, refresh, session check (calls backend auth endpoints)

**IMPORTANT**: No `@supabase/supabase-js` dependency. Frontend NEVER imports Supabase. All auth goes through the backend.

---

## `src/lib/auth.ts`

```typescript
/**
 * lib/auth.ts
 *
 * Auth client — calls backend /api/v1/auth/* endpoints.
 * No Supabase JS dependency.

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error(
    "Missing Supabase environment variables. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.",
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// ─────────────────────────────────────────────
// Auth helpers
// ─────────────────────────────────────────────

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

export async function getSession() {
  return supabase.auth.getSession();
}

// ─────────────────────────────────────────────
// Storage helpers
// ─────────────────────────────────────────────

/**
 * Upload a document file to Supabase Storage.
 *
 * Path format: {userId}/{documentId}/{filename}
 * Bucket: "documents" (must be created in Supabase dashboard)
 *
 * @param file - The file to upload
 * @param userId - Current user's ID
 * @param documentId - UUID for this document (generated before upload)
 * @returns Supabase storage upload result
 */
export async function uploadDocument(
  file: File,
  userId: string,
  documentId: string,
) {
  const path = `${userId}/${documentId}/${file.name}`;
  return supabase.storage.from("documents").upload(path, file, {
    cacheControl: "3600",
    upsert: false,
  });
}

/**
 * Get a signed URL for downloading/viewing a document.
 *
 * @param path - Storage path (userId/documentId/filename)
 * @param expiresIn - URL expiry in seconds (default 3600 = 1 hour)
 */
export async function getDocumentUrl(path: string, expiresIn = 3600) {
  return supabase.storage.from("documents").createSignedUrl(path, expiresIn);
}
```

---

## `src/lib/api.ts`

```typescript
/**
 * lib/api.ts
 *
 * API client for DocMind-VLM backend (FastAPI).
 * All fetch calls go through this module.
 * JWT token is automatically attached from Supabase session.
 *
 * Base URL: import.meta.env.VITE_API_URL (set in frontend/.env)
 */

import { supabase } from "./supabase";
import type {
  DocumentCreate,
  DocumentResponse,
  DocumentListResponse,
  ExtractionResponse,
  AuditEntryResponse,
  OverlayRegion,
  ComparisonResponse,
  ChatHistoryResponse,
  TemplateListResponse,
  HealthResponse,
} from "@/types/api";
import { ApiError } from "@/types/api";

// ─────────────────────────────────────────────
// Base URL
// ─────────────────────────────────────────────

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ─────────────────────────────────────────────
// Core fetch helper
// ─────────────────────────────────────────────

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  // Get current session JWT
  const {
    data: { session },
  } = await supabase.auth.getSession();
  const token = session?.access_token;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers as Record<string, string>),
  };

  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(response.status, detail);
  }

  return response.json() as Promise<T>;
}

// ─────────────────────────────────────────────
// Document API
// ─────────────────────────────────────────────

/**
 * POST /api/v1/documents
 *
 * Create a document record after file upload.
 */
export async function createDocument(
  data: DocumentCreate,
): Promise<DocumentResponse> {
  return apiFetch<DocumentResponse>("/api/v1/documents", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/**
 * GET /api/v1/documents?page=N&limit=N
 *
 * Fetch paginated document list for the current user.
 */
export async function fetchDocuments(
  page: number,
  limit: number,
): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>(
    `/api/v1/documents?page=${page}&limit=${limit}`,
  );
}

/**
 * GET /api/v1/documents/:id
 *
 * Fetch a single document by ID.
 */
export async function fetchDocument(id: string): Promise<DocumentResponse> {
  return apiFetch<DocumentResponse>(`/api/v1/documents/${id}`);
}

/**
 * DELETE /api/v1/documents/:id
 *
 * Delete a document and its associated data.
 */
export async function deleteDocument(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/documents/${id}`, { method: "DELETE" });
}

/**
 * POST /api/v1/documents/:id/process (SSE)
 *
 * Trigger document processing pipeline. Streams step-by-step progress events.
 * Uses fetch + ReadableStream — EventSource only supports GET, this is a POST.
 *
 * @returns AbortController to cancel the stream
 */
export function processDocument(
  id: string,
  templateType: string | undefined,
  onMessage: (data: unknown) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
): AbortController {
  return createSSEStream(
    `/api/v1/documents/${id}/process`,
    { template_type: templateType ?? null },
    onMessage,
    onError,
    onComplete,
  );
}

// ─────────────────────────────────────────────
// Extraction API
// ─────────────────────────────────────────────

/**
 * GET /api/v1/extractions/:document_id
 *
 * Fetch extraction results for a processed document.
 */
export async function fetchExtraction(
  documentId: string,
): Promise<ExtractionResponse> {
  return apiFetch<ExtractionResponse>(
    `/api/v1/extractions/${documentId}`,
  );
}

/**
 * GET /api/v1/extractions/:document_id/audit
 *
 * Fetch the pipeline audit trail for transparency.
 */
export async function fetchAuditTrail(
  documentId: string,
): Promise<AuditEntryResponse[]> {
  return apiFetch<AuditEntryResponse[]>(
    `/api/v1/extractions/${documentId}/audit`,
  );
}

/**
 * GET /api/v1/extractions/:document_id/overlay
 *
 * Fetch overlay regions for document viewer visualization.
 */
export async function fetchOverlay(
  documentId: string,
): Promise<OverlayRegion[]> {
  return apiFetch<OverlayRegion[]>(
    `/api/v1/extractions/${documentId}/overlay`,
  );
}

/**
 * GET /api/v1/extractions/:document_id/comparison
 *
 * Fetch raw vs post-processed extraction comparison.
 */
export async function fetchComparison(
  documentId: string,
): Promise<ComparisonResponse> {
  return apiFetch<ComparisonResponse>(
    `/api/v1/extractions/${documentId}/comparison`,
  );
}

// ─────────────────────────────────────────────
// Chat API
// ─────────────────────────────────────────────

/**
 * POST /api/v1/chat/:document_id (SSE)
 *
 * Send a chat message and stream the response via SSE.
 * Uses fetch + ReadableStream — EventSource only supports GET, this is a POST.
 *
 * @returns AbortController to cancel the stream
 */
export function sendChatMessage(
  documentId: string,
  message: string,
  onMessage: (data: unknown) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
): AbortController {
  return createSSEStream(
    `/api/v1/chat/${documentId}`,
    { message },
    onMessage,
    onError,
    onComplete,
  );
}

/**
 * GET /api/v1/chat/:document_id/history?page=N&limit=N
 *
 * Fetch paginated chat history for a document.
 */
export async function fetchChatHistory(
  documentId: string,
  page: number,
  limit: number,
): Promise<ChatHistoryResponse> {
  return apiFetch<ChatHistoryResponse>(
    `/api/v1/chat/${documentId}/history?page=${page}&limit=${limit}`,
  );
}

// ─────────────────────────────────────────────
// SSE Stream Helper (for POST-based SSE)
// ─────────────────────────────────────────────

/**
 * Create a streaming SSE connection using fetch + ReadableStream.
 *
 * Used for endpoints that require POST body (process, chat).
 * EventSource only supports GET, so this handles POST-based SSE.
 *
 * @param path - API path (e.g., /api/v1/chat/:id)
 * @param body - JSON body to send
 * @param onMessage - called for each SSE event
 * @param onError - called on stream error
 * @param onComplete - called when stream ends
 * @returns AbortController to cancel the stream
 */
export function createSSEStream(
  path: string,
  body: Record<string, unknown>,
  onMessage: (data: unknown) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      const response = await fetch(`${BASE_URL}${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try {
          const errorBody = await response.json();
          detail = errorBody.detail ?? detail;
        } catch {
          detail = response.statusText || detail;
        }
        throw new ApiError(response.status, detail);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No readable stream");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6).trim();
            if (jsonStr === "[DONE]") {
              onComplete();
              return;
            }
            try {
              const data = JSON.parse(jsonStr);
              onMessage(data);
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      }

      onComplete();
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}

// ─────────────────────────────────────────────
// Templates API
// ─────────────────────────────────────────────

/**
 * GET /api/v1/templates
 *
 * Fetch all available extraction templates.
 */
export async function fetchTemplates(): Promise<TemplateListResponse> {
  return apiFetch<TemplateListResponse>("/api/v1/templates");
}

// ─────────────────────────────────────────────
// Health
// ─────────────────────────────────────────────

/**
 * GET /api/v1/health/status
 *
 * Check API health and service status.
 */
export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/v1/health/status");
}
```

---

## `src/types/api.ts`

TypeScript types that mirror the backend API spec **exactly**. When the API spec changes, update here first.

```typescript
/**
 * types/api.ts
 *
 * TypeScript types mirroring the DocMind-VLM backend API (FastAPI + Pydantic).
 * Source of truth: backend Pydantic schemas in docmind/modules/*/schemas.py
 */

// ─────────────────────────────────────────────
// Shared types
// ─────────────────────────────────────────────

export type DocumentStatus =
  | "uploaded"
  | "processing"
  | "ready"
  | "error";

// ─────────────────────────────────────────────
// Document
// ─────────────────────────────────────────────

export interface DocumentCreate {
  filename: string;
  file_type: string;
  file_size: number;
  storage_path: string;
}

export interface DocumentResponse {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: DocumentStatus;
  document_type: string | null;
  page_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentResponse[];
  total: number;
  page: number;
  limit: number;
}

// ─────────────────────────────────────────────
// Extraction
// ─────────────────────────────────────────────

export interface BoundingBox {
  x: number;      // 0.0–1.0 normalized
  y: number;      // 0.0–1.0 normalized
  width: number;  // 0.0–1.0 normalized
  height: number; // 0.0–1.0 normalized
}

export interface ExtractedFieldResponse {
  id: string;
  field_type: string;        // key_value | table_cell | entity | text_block
  field_key: string | null;
  field_value: string;
  page_number: number;
  bounding_box: BoundingBox;
  confidence: number;        // 0.0–1.0
  vlm_confidence: number;    // 0.0–1.0
  cv_quality_score: number;  // 0.0–1.0
  is_required: boolean;
  is_missing: boolean;
}

export interface ExtractionResponse {
  id: string;
  document_id: string;
  mode: string;              // general | template
  template_type: string | null;
  fields: ExtractedFieldResponse[];
  processing_time_ms: number;
  created_at: string;
}

// ─────────────────────────────────────────────
// Audit trail
// ─────────────────────────────────────────────

export interface AuditEntryResponse {
  step_name: string;
  step_order: number;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  parameters: Record<string, unknown>;
  duration_ms: number;
}

// ─────────────────────────────────────────────
// Overlay
// ─────────────────────────────────────────────

export interface OverlayRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  color: string;          // hex — "#22c55e" (≥0.8), "#eab308" (≥0.5), "#ef4444" (<0.5)
  tooltip: string | null;
}

// ─────────────────────────────────────────────
// Comparison (enhanced vs raw extraction)
// ─────────────────────────────────────────────

export interface ComparisonResponse {
  enhanced_fields: ExtractedFieldResponse[];
  raw_fields: Record<string, unknown>[];
  corrected: string[];    // field IDs corrected by pipeline
  added: string[];        // field IDs added by pipeline
}

// ─────────────────────────────────────────────
// Chat
// ─────────────────────────────────────────────

export interface Citation {
  page: number;
  bounding_box: BoundingBox;
  text_span: string;
}

export interface ChatMessageRequest {
  message: string;
}

export interface ChatMessageResponse {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface ChatHistoryResponse {
  items: ChatMessageResponse[];
  total: number;
  page: number;
  limit: number;
}

// ─────────────────────────────────────────────
// Templates
// ─────────────────────────────────────────────

export interface TemplateResponse {
  type: string;
  name: string;
  description: string;
  required_fields: string[];
  optional_fields: string[];
}

export interface TemplateListResponse {
  items: TemplateResponse[];
}

// ─────────────────────────────────────────────
// Health
// ─────────────────────────────────────────────

export interface HealthComponentResponse {
  name: string;
  status: string;                  // "healthy" | "unhealthy"
  message: string | null;
  response_time_ms: number | null;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  components: HealthComponentResponse[];
  uptime_seconds: number;
}

// ─────────────────────────────────────────────
// Client-side error type
// ─────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}
```

---

## Error Handling in Components

Use `ApiError` to distinguish API errors from network errors:

```typescript
// In component error handling
try {
  const response = await fetchExtraction(documentId);
  // ...
} catch (err) {
  if (err instanceof ApiError) {
    // Known API error — show specific message
    if (err.statusCode === 404) {
      setError("Document not found.");
    } else if (err.statusCode === 403) {
      setError("You don't have access to this document.");
    } else {
      setError(`API error (${err.statusCode}): ${err.detail}`);
    }
  } else {
    // Network error (no connection, CORS, etc.)
    setError("Network error. Is the backend running?");
  }
}
```

| Error Type | When | User Message |
|-----------|------|-------------|
| `ApiError(400, ...)` | Invalid request | Show `err.detail` |
| `ApiError(401, ...)` | Session expired | Redirect to login |
| `ApiError(403, ...)` | No access | `"You don't have access to this document."` |
| `ApiError(404, ...)` | Document not found | `"Document not found."` |
| `ApiError(413, ...)` | File too large | `"File too large. Maximum 20 MB."` |
| `ApiError(422, ...)` | Validation fail | Show `err.detail` |
| `ApiError(500, ...)` | Backend crash | `"Server error. Please try again."` |
| `TypeError: Failed to fetch` | Backend not running / CORS | `"Network error. Is the backend running?"` |

---

## Vite Environment Variables

```bash
# frontend/.env (development)
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...your-anon-key

# frontend/.env.production
VITE_API_URL=https://api.docmind-vlm.com
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...your-anon-key
```

**Rules:**
- All Vite env vars **must** be prefixed with `VITE_`
- Access with `import.meta.env.VITE_API_URL` — NOT `process.env.*`
- Provide a fallback in `api.ts`: `?? "http://localhost:8000"` for local dev without `.env`
- Supabase vars have **no fallback** — fail fast with clear error if missing
- Never commit `.env` files with secrets — `.env.example` only

---

## `vite.config.ts` — Dev Proxy (Optional)

```typescript
// vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

With this proxy, `VITE_API_URL` can be empty and requests to `/api/*` forward to FastAPI.

---

## TypeScript Import Rules

```typescript
// Use type imports for types only
import type { ExtractionResponse, Citation } from "@/types/api";

// Use value import for class (needed at runtime)
import { ApiError } from "@/types/api";

// Use path alias @/ for src-relative imports
import { fetchExtraction } from "@/lib/api";
import { supabase } from "@/lib/supabase";

// WRONG: Don't use relative paths from deeply nested files
import { fetchExtraction } from "../../../lib/api";
```

The `@/` alias is configured in `vite.config.ts` and `tsconfig.json`.

---

## `tsconfig.json` Path Aliases

```json
{
  "compilerOptions": {
    "strict": true,
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "paths": {
      "@/*": ["./src/*"]
    },
    "baseUrl": "."
  },
  "include": ["src"]
}
```
