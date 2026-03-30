import { useAuthStore } from "@/stores/auth-store";
import { refreshSession } from "@/lib/auth";
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
  ProjectResponse,
  ProjectListResponse,
  ProjectDocumentResponse,
  PersonaResponse,
  ConversationResponse,
  ConversationDetailResponse,
} from "@/types/api";
import { ApiError, TemplateDetail } from "@/types/api";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8009";

function getToken(): string | null {
  return useAuthStore.getState().accessToken;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
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
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<DocumentResponse> {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${BASE_URL}/api/v1/documents`, {
    method: "POST",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: formData,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try { const body = await response.json(); detail = body.detail ?? detail; } catch { detail = response.statusText || detail; }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<DocumentResponse>;
}

export async function fetchDocuments(page: number, limit: number, standalone = false): Promise<DocumentListResponse> {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (standalone) params.set("standalone", "true");
  return apiFetch<DocumentListResponse>(`/api/v1/documents?${params}`);
}

export async function fetchDocument(id: string): Promise<DocumentResponse> {
  return apiFetch<DocumentResponse>(`/api/v1/documents/${id}`);
}

export async function fetchDocumentUrl(id: string): Promise<{ url: string }> {
  return apiFetch<{ url: string }>(`/api/v1/documents/${id}/url`);
}

export async function deleteDocument(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/documents/${id}`, { method: "DELETE" });
}

export function processDocument(
  id: string, templateType: string | undefined,
  onMessage: (data: unknown) => void, onError: (error: Error) => void, onComplete: () => void,
): AbortController {
  return createSSEStream(`/api/v1/extractions/${id}/process`, { template_type: templateType ?? null }, onMessage, onError, onComplete);
}

export async function fetchExtraction(documentId: string): Promise<ExtractionResponse> {
  return apiFetch<ExtractionResponse>(`/api/v1/extractions/${documentId}`);
}

export async function fetchAuditTrail(documentId: string): Promise<AuditEntryResponse[]> {
  return apiFetch<AuditEntryResponse[]>(`/api/v1/extractions/${documentId}/audit`);
}

export async function fetchOverlay(documentId: string): Promise<OverlayRegion[]> {
  return apiFetch<OverlayRegion[]>(`/api/v1/extractions/${documentId}/overlay`);
}

export async function fetchComparison(documentId: string): Promise<ComparisonResponse> {
  return apiFetch<ComparisonResponse>(`/api/v1/extractions/${documentId}/comparison`);
}

export function sendChatMessage(
  documentId: string, message: string,
  onMessage: (data: unknown) => void, onError: (error: Error) => void, onComplete: () => void,
): AbortController {
  return createSSEStream(`/api/v1/chat/${documentId}`, { message }, onMessage, onError, onComplete);
}

export async function fetchChatHistory(documentId: string, page: number, limit: number): Promise<ChatHistoryResponse> {
  return apiFetch<ChatHistoryResponse>(`/api/v1/chat/${documentId}/history?page=${page}&limit=${limit}`);
}

export function createSSEStream(
  path: string, body: Record<string, unknown>,
  onMessage: (data: unknown) => void, onError: (error: Error) => void, onComplete: () => void,
): AbortController {
  const controller = new AbortController();
  (async () => {
    try {
      const token = getToken();
      const response = await fetch(`${BASE_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try { const errorBody = await response.json(); detail = errorBody.detail ?? detail; } catch { detail = response.statusText || detail; }
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
            if (jsonStr === "[DONE]") { onComplete(); return; }
            try { onMessage(JSON.parse(jsonStr)); } catch { /* skip malformed */ }
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

export async function fetchTemplates(): Promise<TemplateListResponse> {
  return apiFetch<TemplateListResponse>("/api/v1/templates");
}

export async function fetchTemplateDetail(templateId: string): Promise<TemplateDetail> {
  return apiFetch<TemplateDetail>(`/api/v1/templates/${templateId}`);
}

export async function createTemplate(data: Record<string, unknown> | object): Promise<TemplateDetail> {
  return apiFetch<TemplateDetail>("/api/v1/templates", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateTemplate(templateId: string, data: Record<string, unknown> | object): Promise<TemplateDetail> {
  return apiFetch<TemplateDetail>(`/api/v1/templates/${templateId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteTemplate(templateId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/templates/${templateId}`, { method: "DELETE" });
}

export async function duplicateTemplate(templateId: string): Promise<TemplateDetail> {
  return apiFetch<TemplateDetail>(`/api/v1/templates/${templateId}/duplicate`, { method: "POST" });
}

export async function fetchProjectChunks(
  projectId: string, documentId?: string
): Promise<{ total: number; items: Record<string, unknown>[] }> {
  const params = new URLSearchParams();
  if (documentId) params.set("document_id", documentId);
  return apiFetch(`/api/v1/projects/${projectId}/chunks?${params}`);
}

export async function fetchAnalytics(): Promise<Record<string, unknown>> {
  return apiFetch("/api/v1/analytics/summary");
}

export async function checkHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/api/v1/health/status");
}

// Projects
export async function fetchProjects(page = 1, limit = 20): Promise<ProjectListResponse> {
  return apiFetch<ProjectListResponse>(`/api/v1/projects?page=${page}&limit=${limit}`);
}

export async function fetchProject(id: string): Promise<ProjectResponse> {
  return apiFetch<ProjectResponse>(`/api/v1/projects/${id}`);
}

export async function createProject(data: { name: string; description?: string; persona_id?: string }): Promise<ProjectResponse> {
  return apiFetch<ProjectResponse>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) });
}

export async function updateProject(id: string, data: { name?: string; description?: string; persona_id?: string }): Promise<ProjectResponse> {
  return apiFetch<ProjectResponse>(`/api/v1/projects/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deleteProject(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
}

export async function addDocumentToProject(projectId: string, file: File): Promise<ProjectDocumentResponse> {
  // Step 1: Upload file as a document
  const doc = await uploadDocument(file);

  // Step 2: Link the document to the project
  return apiFetch<ProjectDocumentResponse>(
    `/api/v1/projects/${projectId}/documents?document_id=${doc.id}`,
    { method: "POST" },
  );
}

export async function fetchProjectDocuments(projectId: string): Promise<ProjectDocumentResponse[]> {
  return apiFetch<ProjectDocumentResponse[]>(`/api/v1/projects/${projectId}/documents`);
}

export async function removeProjectDocument(projectId: string, docId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/projects/${projectId}/documents/${docId}`, { method: "DELETE" });
}

export function sendProjectChat(
  projectId: string, message: string, conversationId: string | null,
  onMessage: (data: unknown) => void, onError: (error: Error) => void, onComplete: () => void,
): AbortController {
  return createSSEStream(`/api/v1/projects/${projectId}/chat`, { message, conversation_id: conversationId }, onMessage, onError, onComplete);
}

export async function fetchProjectConversations(projectId: string): Promise<ConversationResponse[]> {
  return apiFetch<ConversationResponse[]>(`/api/v1/projects/${projectId}/conversations`);
}

export async function fetchConversation(projectId: string, convId: string): Promise<ConversationDetailResponse> {
  return apiFetch<ConversationDetailResponse>(`/api/v1/projects/${projectId}/conversations/${convId}`);
}

export async function deleteConversation(projectId: string, convId: string): Promise<void> {
  await apiFetch<void>(`/api/v1/projects/${projectId}/conversations/${convId}`, { method: "DELETE" });
}

// Personas
export async function fetchPersonas(): Promise<PersonaResponse[]> {
  return apiFetch<PersonaResponse[]>("/api/v1/personas");
}

export async function createPersona(data: { name: string; description?: string; system_prompt: string; tone?: string; rules?: string; boundaries?: string }): Promise<PersonaResponse> {
  return apiFetch<PersonaResponse>("/api/v1/personas", { method: "POST", body: JSON.stringify(data) });
}

export async function updatePersona(id: string, data: Partial<{ name: string; description: string; system_prompt: string; tone: string; rules: string; boundaries: string }>): Promise<PersonaResponse> {
  return apiFetch<PersonaResponse>(`/api/v1/personas/${id}`, { method: "PUT", body: JSON.stringify(data) });
}

export async function deletePersona(id: string): Promise<void> {
  await apiFetch<void>(`/api/v1/personas/${id}`, { method: "DELETE" });
}

export async function duplicatePersona(id: string): Promise<PersonaResponse> {
  return apiFetch<PersonaResponse>(`/api/v1/personas/${id}/duplicate`, { method: "POST" });
}
