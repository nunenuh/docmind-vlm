import { useNavigate } from "react-router-dom";
import { FileText, Image, Trash2, Clock, CheckCircle, AlertCircle, Loader2, Database } from "lucide-react";
import type { DocumentResponse, DocumentStatus } from "@/types/api";
import { useIndexDocument } from "@/hooks/useEmbedding";

const statusConfig: Record<DocumentStatus, { icon: React.ReactNode; label: string; dotClass: string }> = {
  uploaded: { icon: <Clock className="w-3 h-3" />, label: "Uploaded", dotClass: "bg-gray-400" },
  processing: { icon: <Loader2 className="w-3 h-3 animate-spin" />, label: "Processing", dotClass: "bg-indigo-400" },
  ready: { icon: <CheckCircle className="w-3 h-3" />, label: "Ready", dotClass: "bg-emerald-400" },
  error: { icon: <AlertCircle className="w-3 h-3" />, label: "Error", dotClass: "bg-rose-400" },
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isImageType(fileType: string): boolean {
  return ["png", "jpg", "jpeg", "webp", "gif", "tiff", "bmp"].includes(fileType.toLowerCase());
}

interface DocumentCardProps {
  document: DocumentResponse;
  onDelete: (id: string) => void;
}

export function DocumentCard({ document, onDelete }: DocumentCardProps) {
  const navigate = useNavigate();
  const status = statusConfig[document.status];
  const isImage = isImageType(document.file_type);
  const indexDoc = useIndexDocument();

  const handleIndex = (e: React.MouseEvent) => {
    e.stopPropagation();
    indexDoc.mutate(document.id);
  };

  return (
    <div
      onClick={() => navigate(`/workspace/${document.id}`)}
      className="group bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4 cursor-pointer hover:border-[#2a2a3a] transition-all duration-200 focus-within:ring-2 focus-within:ring-indigo-500"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
              isImage
                ? "bg-emerald-500/10 group-hover:bg-emerald-500/15"
                : "bg-indigo-500/10 group-hover:bg-indigo-500/15"
            }`}
          >
            {isImage ? (
              <Image className="w-5 h-5 text-emerald-400" />
            ) : (
              <FileText className="w-5 h-5 text-indigo-400" />
            )}
          </div>
          <div className="min-w-0">
            <h3 className="text-white font-medium truncate text-sm">{document.filename}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{formatDate(document.created_at)}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleIndex}
            disabled={indexDoc.isPending}
            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md hover:bg-indigo-500/10 text-gray-500 hover:text-indigo-400 transition-all duration-200 focus:outline-none focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:opacity-50"
            aria-label="Index document for RAG"
            title="Index for RAG search"
          >
            {indexDoc.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Database className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(document.id);
            }}
            className="opacity-0 group-hover:opacity-100 p-1.5 rounded-md hover:bg-rose-500/10 text-gray-500 hover:text-rose-400 transition-all duration-200 focus:outline-none focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-rose-500"
            aria-label="Delete document"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-400">
          <span className={`w-1.5 h-1.5 rounded-full ${status.dotClass}`} />
          {status.label}
        </span>
        <span className="text-xs text-gray-500 bg-white/5 px-2 py-0.5 rounded font-medium">
          {document.file_type.toUpperCase()}
        </span>
        <span className="text-xs text-gray-600 ml-auto">
          {formatFileSize(document.file_size)}
        </span>
      </div>
    </div>
  );
}
