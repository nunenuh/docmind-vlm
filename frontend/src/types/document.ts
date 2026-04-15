export interface EmbeddingModelInfo {
  model: string;
  provider: string;
  chunks: number;
  last_embedded: string;
}

export interface EmbeddingStatusResponse {
  current_model: string;
  status: "indexed" | "partial" | "not_indexed" | "no_chunks";
  indexed_chunks: number;
  total_chunks: number;
  available_models: EmbeddingModelInfo[];
}

export interface IndexDocumentResponse {
  document_id: string;
  model: string;
  chunks_indexed: number;
  status: string;
}
