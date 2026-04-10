export type TokenScope =
  | "documents:read" | "documents:write"
  | "extractions:read" | "extractions:write"
  | "projects:read" | "projects:write" | "projects:chat"
  | "rag:read"
  | "templates:read" | "templates:write"
  | "personas:read" | "personas:write"
  | "admin:*";

export interface ScopeInfo {
  scope: TokenScope;
  label: string;
  description: string;
  module: string;
}

export interface CreateTokenRequest {
  name: string;
  scopes: TokenScope[];
  token_type: "live" | "test";
  expires_in_days: number | null;
}

export interface UpdateTokenRequest {
  name?: string;
  scopes?: TokenScope[];
}

export interface TokenResponse {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  token_type: string;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
}

export interface TokenCreatedResponse extends TokenResponse {
  plain_token: string;
}

export interface TokenListResponse {
  tokens: TokenResponse[];
  total: number;
}

export interface EndpointInfo {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  scope: TokenScope;
  description: string;
  module: string;
}
