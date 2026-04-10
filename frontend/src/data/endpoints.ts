import type { EndpointInfo } from "@/types/api-token";

export const ENDPOINT_DEFINITIONS: EndpointInfo[] = [
  // Documents
  {
    method: "GET",
    path: "/api/v1/documents",
    scope: "documents:read",
    description: "List all documents",
    module: "Documents",
  },
  {
    method: "GET",
    path: "/api/v1/documents/{id}",
    scope: "documents:read",
    description: "Get a single document by ID",
    module: "Documents",
  },
  {
    method: "GET",
    path: "/api/v1/documents/{id}/file",
    scope: "documents:read",
    description: "Download the original document file",
    module: "Documents",
  },
  {
    method: "GET",
    path: "/api/v1/documents/search",
    scope: "documents:read",
    description: "Search documents by filename or content",
    module: "Documents",
  },
  {
    method: "POST",
    path: "/api/v1/documents",
    scope: "documents:write",
    description: "Upload a new document (PDF or image)",
    module: "Documents",
  },
  {
    method: "DELETE",
    path: "/api/v1/documents/{id}",
    scope: "documents:write",
    description: "Delete a document and its associated data",
    module: "Documents",
  },
  {
    method: "POST",
    path: "/api/v1/documents/{id}/process",
    scope: "documents:write",
    description: "Process a document through the extraction pipeline (SSE)",
    module: "Documents",
  },

  // Extractions
  {
    method: "GET",
    path: "/api/v1/extractions/{document_id}",
    scope: "extractions:read",
    description: "Get extraction results for a document",
    module: "Extractions",
  },
  {
    method: "GET",
    path: "/api/v1/extractions/{document_id}/audit",
    scope: "extractions:read",
    description: "Get the extraction audit trail",
    module: "Extractions",
  },
  {
    method: "GET",
    path: "/api/v1/extractions/{document_id}/overlay",
    scope: "extractions:read",
    description: "Get bounding box overlay regions",
    module: "Extractions",
  },
  {
    method: "GET",
    path: "/api/v1/extractions/{document_id}/comparison",
    scope: "extractions:read",
    description: "Get field comparison data",
    module: "Extractions",
  },
  {
    method: "GET",
    path: "/api/v1/extractions/{document_id}/export",
    scope: "extractions:read",
    description: "Export extraction results",
    module: "Extractions",
  },
  {
    method: "POST",
    path: "/api/v1/extractions/{document_id}/process",
    scope: "extractions:write",
    description: "Process extraction for a document (SSE)",
    module: "Extractions",
  },
  {
    method: "POST",
    path: "/api/v1/extractions/classify",
    scope: "extractions:write",
    description: "Classify a document type",
    module: "Extractions",
  },

  // Chat (document-level)
  {
    method: "POST",
    path: "/api/v1/chat/{document_id}",
    scope: "documents:write",
    description: "Send a chat message about a document (SSE)",
    module: "Documents",
  },
  {
    method: "GET",
    path: "/api/v1/chat/{document_id}/history",
    scope: "documents:read",
    description: "Get chat history for a document",
    module: "Documents",
  },

  // Templates
  {
    method: "GET",
    path: "/api/v1/templates",
    scope: "templates:read",
    description: "List all extraction templates",
    module: "Templates",
  },
  {
    method: "POST",
    path: "/api/v1/templates",
    scope: "templates:write",
    description: "Create a new extraction template",
    module: "Templates",
  },

  // Projects
  {
    method: "GET",
    path: "/api/v1/projects",
    scope: "projects:read",
    description: "List all projects",
    module: "Projects",
  },
  {
    method: "GET",
    path: "/api/v1/projects/{id}",
    scope: "projects:read",
    description: "Get a single project by ID",
    module: "Projects",
  },
  {
    method: "POST",
    path: "/api/v1/projects",
    scope: "projects:write",
    description: "Create a new project",
    module: "Projects",
  },
  {
    method: "PUT",
    path: "/api/v1/projects/{id}",
    scope: "projects:write",
    description: "Update an existing project",
    module: "Projects",
  },
  {
    method: "DELETE",
    path: "/api/v1/projects/{id}",
    scope: "projects:write",
    description: "Delete a project",
    module: "Projects",
  },
  {
    method: "POST",
    path: "/api/v1/projects/{id}/documents",
    scope: "projects:write",
    description: "Add a document to a project",
    module: "Projects",
  },
  {
    method: "GET",
    path: "/api/v1/projects/{id}/documents",
    scope: "projects:read",
    description: "List documents in a project",
    module: "Projects",
  },
  {
    method: "DELETE",
    path: "/api/v1/projects/{id}/documents/{doc_id}",
    scope: "projects:write",
    description: "Remove a document from a project",
    module: "Projects",
  },
  {
    method: "POST",
    path: "/api/v1/projects/{id}/chat",
    scope: "projects:chat",
    description: "Send a chat message in a project conversation (SSE)",
    module: "Projects",
  },
  {
    method: "GET",
    path: "/api/v1/projects/{id}/conversations",
    scope: "projects:read",
    description: "List conversations in a project",
    module: "Projects",
  },
  {
    method: "GET",
    path: "/api/v1/projects/{id}/conversations/{conv_id}",
    scope: "projects:read",
    description: "Get a single conversation with messages",
    module: "Projects",
  },
  {
    method: "DELETE",
    path: "/api/v1/projects/{id}/conversations/{conv_id}",
    scope: "projects:write",
    description: "Delete a conversation",
    module: "Projects",
  },

  // Personas
  {
    method: "GET",
    path: "/api/v1/personas",
    scope: "personas:read",
    description: "List all AI personas",
    module: "Personas",
  },
  {
    method: "POST",
    path: "/api/v1/personas",
    scope: "personas:write",
    description: "Create a new AI persona",
    module: "Personas",
  },
  {
    method: "PUT",
    path: "/api/v1/personas/{id}",
    scope: "personas:write",
    description: "Update an existing persona",
    module: "Personas",
  },
  {
    method: "DELETE",
    path: "/api/v1/personas/{id}",
    scope: "personas:write",
    description: "Delete a persona",
    module: "Personas",
  },

  // RAG
  {
    method: "POST",
    path: "/api/v1/rag/search",
    scope: "rag:read",
    description: "Search the RAG index with a query",
    module: "RAG",
  },
  {
    method: "GET",
    path: "/api/v1/rag/chunks",
    scope: "rag:read",
    description: "List RAG chunks with optional filters",
    module: "RAG",
  },
  {
    method: "GET",
    path: "/api/v1/rag/chunks/{chunk_id}",
    scope: "rag:read",
    description: "Get a single RAG chunk by ID",
    module: "RAG",
  },
  {
    method: "GET",
    path: "/api/v1/rag/stats",
    scope: "rag:read",
    description: "Get RAG index statistics",
    module: "RAG",
  },

  // Analytics
  {
    method: "GET",
    path: "/api/v1/analytics/summary",
    scope: "documents:read",
    description: "Get analytics summary (document counts, storage, etc.)",
    module: "Documents",
  },
];

export const ENDPOINT_MODULES = [
  "Documents",
  "Extractions",
  "Templates",
  "Projects",
  "Personas",
  "RAG",
] as const;
