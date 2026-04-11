export type ProviderType = "vlm" | "embedding";
export type ProviderName = "dashscope" | "openai" | "google" | "ollama";

export interface SetProviderRequest {
  provider_name: ProviderName;
  api_key: string;
  model_name: string;
  base_url?: string | null;
}

export interface ValidateProviderRequest {
  provider_name: ProviderName;
  api_key: string;
  base_url?: string | null;
}

export interface ValidateProviderResponse {
  success: boolean;
  models: string[];
  error?: string | null;
}

export interface ProviderConfigResponse {
  provider_type: ProviderType;
  provider_name: ProviderName;
  model_name: string;
  base_url: string | null;
  is_validated: boolean;
  api_key_prefix: string;
  created_at: string;
  updated_at: string;
}

export interface ProvidersResponse {
  vlm: ProviderConfigResponse | null;
  embedding: ProviderConfigResponse | null;
}
