import type { ScopeInfo } from "@/types/api-token";

export const SCOPE_DEFINITIONS: ScopeInfo[] = [
  // Documents
  {
    scope: "documents:read",
    label: "Read Documents",
    description: "List, view, and download documents",
    module: "Documents",
  },
  {
    scope: "documents:write",
    label: "Write Documents",
    description: "Upload, update, and delete documents",
    module: "Documents",
  },

  // Extractions
  {
    scope: "extractions:read",
    label: "Read Extractions",
    description: "View extraction results, audit trails, overlays, and comparisons",
    module: "Extractions",
  },
  {
    scope: "extractions:write",
    label: "Write Extractions",
    description: "Process documents, classify, and export extractions",
    module: "Extractions",
  },

  // Projects
  {
    scope: "projects:read",
    label: "Read Projects",
    description: "List and view projects, conversations, and project documents",
    module: "Projects",
  },
  {
    scope: "projects:write",
    label: "Write Projects",
    description: "Create, update, and delete projects and project documents",
    module: "Projects",
  },
  {
    scope: "projects:chat",
    label: "Project Chat",
    description: "Send messages in project conversations",
    module: "Projects",
  },

  // RAG
  {
    scope: "rag:read",
    label: "Read RAG",
    description: "Search RAG index, view chunks and statistics",
    module: "RAG",
  },

  // Templates
  {
    scope: "templates:read",
    label: "Read Templates",
    description: "List and view extraction templates",
    module: "Templates",
  },
  {
    scope: "templates:write",
    label: "Write Templates",
    description: "Create, update, and delete extraction templates",
    module: "Templates",
  },

  // Personas
  {
    scope: "personas:read",
    label: "Read Personas",
    description: "List and view AI personas",
    module: "Personas",
  },
  {
    scope: "personas:write",
    label: "Write Personas",
    description: "Create, update, and delete AI personas",
    module: "Personas",
  },

  // Admin
  {
    scope: "admin:*",
    label: "Admin (Full Access)",
    description: "Full access to all API endpoints and administrative actions",
    module: "Admin",
  },
];

export const SCOPE_MODULES = [
  "Documents",
  "Extractions",
  "Projects",
  "RAG",
  "Templates",
  "Personas",
  "Admin",
] as const;
