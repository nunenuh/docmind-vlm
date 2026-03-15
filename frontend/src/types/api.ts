export type DocumentStatus = "uploaded" | "processing" | "ready" | "error";

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

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ExtractedFieldResponse {
  id: string;
  field_type: string;
  field_key: string | null;
  field_value: string;
  page_number: number;
  bounding_box: BoundingBox;
  confidence: number;
  vlm_confidence: number;
  cv_quality_score: number;
  is_required: boolean;
  is_missing: boolean;
}

export interface ExtractionResponse {
  id: string;
  document_id: string;
  mode: string;
  template_type: string | null;
  fields: ExtractedFieldResponse[];
  processing_time_ms: number;
  created_at: string;
}

export interface AuditEntryResponse {
  step_name: string;
  step_order: number;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  parameters: Record<string, unknown>;
  duration_ms: number;
}

export interface OverlayRegion {
  x: number;
  y: number;
  width: number;
  height: number;
  confidence: number;
  color: string;
  tooltip: string | null;
}

export interface ComparisonResponse {
  enhanced_fields: ExtractedFieldResponse[];
  raw_fields: Record<string, unknown>[];
  corrected: string[];
  added: string[];
}

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

export interface HealthComponentResponse {
  name: string;
  status: string;
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

export class ApiError extends Error {
  constructor(
    public statusCode: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}
