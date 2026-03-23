import { useState } from "react";
import { Database, FileText, ChevronDown, ChevronUp, Hash, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchProjectChunks } from "@/lib/api";

interface Chunk {
  id: string;
  document_id: string;
  page_number: number;
  chunk_index: number;
  content: string;
  raw_content: string;
  content_hash: string;
  metadata: string | null;
  created_at: string | null;
}

interface ChunkBrowserProps {
  projectId: string;
  documentId?: string | null;
}

export function ChunkBrowser({ projectId, documentId }: ChunkBrowserProps) {
  const params = new URLSearchParams();
  if (documentId) params.set("document_id", documentId);

  const { data, isLoading } = useQuery({
    queryKey: ["project-chunks", projectId, documentId],
    queryFn: () => fetchProjectChunks(projectId, documentId ?? undefined),
    enabled: !!projectId,
  });

  const chunks = (data?.items ?? []) as unknown as Chunk[];
  const total = data?.total ?? 0;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
      </div>
    );
  }

  if (chunks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <Database className="w-8 h-8 text-gray-600 mb-3" />
        <p className="text-sm text-gray-400">No RAG chunks indexed</p>
        <p className="text-xs text-gray-600 mt-1">Upload documents to this project to generate chunks</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between px-3 py-2">
        <span className="text-xs text-gray-500">{total} chunks indexed</span>
      </div>
      <div className="max-h-[60vh] overflow-y-auto space-y-1 px-1">
        {chunks.map((chunk) => (
          <ChunkCard key={chunk.id} chunk={chunk} />
        ))}
      </div>
    </div>
  );
}

function ChunkCard({ chunk }: { chunk: Chunk }) {
  const [expanded, setExpanded] = useState(false);

  let metadata: Record<string, string> = {};
  try {
    if (chunk.metadata) metadata = JSON.parse(chunk.metadata);
  } catch { /* ignore */ }

  return (
    <div
      className="bg-[#12121a] border border-[#1e1e2e] rounded-lg hover:border-[#2a2a3a] transition-colors cursor-pointer"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-2 px-3 py-2.5">
        <div className="flex items-center gap-1.5 flex-shrink-0 mt-0.5">
          <FileText className="w-3.5 h-3.5 text-gray-600" />
          <span className="text-[10px] text-gray-600 font-mono">p.{chunk.page_number}</span>
          <Hash className="w-3 h-3 text-gray-700" />
          <span className="text-[10px] text-gray-600 font-mono">{chunk.chunk_index}</span>
        </div>
        <p className="text-xs text-gray-400 flex-1 line-clamp-2 leading-relaxed">
          {chunk.raw_content || chunk.content}
        </p>
        <button className="flex-shrink-0 text-gray-600 mt-0.5">
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-[#1e1e2e] px-3 py-3 space-y-2">
          <div>
            <span className="text-[10px] font-medium text-gray-500 uppercase">Full Content</span>
            <pre className="text-xs text-gray-300 mt-1 whitespace-pre-wrap font-mono bg-[#0a0a0f] rounded-lg p-2 max-h-48 overflow-y-auto">
              {chunk.content}
            </pre>
          </div>
          {metadata.filename && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span>File: {metadata.filename}</span>
              {metadata.section_header && <span>Section: {metadata.section_header}</span>}
            </div>
          )}
          <div className="text-[10px] text-gray-600 font-mono truncate">
            Hash: {chunk.content_hash?.slice(0, 16)}...
          </div>
        </div>
      )}
    </div>
  );
}
