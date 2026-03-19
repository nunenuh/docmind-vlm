import { useNavigate } from "react-router-dom";
import { FileText, Trash2, Clock, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import type { DocumentResponse, DocumentStatus } from "@/types/api";

const statusConfig: Record<DocumentStatus, { icon: React.ReactNode; label: string; className: string }> = {
  uploaded: { icon: <Clock className="w-3.5 h-3.5" />, label: "Uploaded", className: "bg-gray-800 text-gray-300" },
  processing: { icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />, label: "Processing", className: "bg-blue-900/50 text-blue-300" },
  ready: { icon: <CheckCircle className="w-3.5 h-3.5" />, label: "Ready", className: "bg-green-900/50 text-green-300" },
  error: { icon: <AlertCircle className="w-3.5 h-3.5" />, label: "Error", className: "bg-red-900/50 text-red-300" },
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

interface DocumentCardProps {
  document: DocumentResponse;
  onDelete: (id: string) => void;
}

export function DocumentCard({ document, onDelete }: DocumentCardProps) {
  const navigate = useNavigate();
  const status = statusConfig[document.status];

  return (
    <div
      onClick={() => navigate(`/workspace/${document.id}`)}
      className="group bg-gray-900/50 border border-gray-800 rounded-xl p-5 cursor-pointer hover:border-blue-500/30 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
            <FileText className="w-5 h-5 text-blue-400" />
          </div>
          <div className="min-w-0">
            <h3 className="text-white font-medium truncate">{document.filename}</h3>
            <p className="text-sm text-gray-500">{formatDate(document.created_at)}</p>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(document.id);
          }}
          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all"
          aria-label="Delete document"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center gap-2">
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full ${status.className}`}>
          {status.icon}
          {status.label}
        </span>
        <span className="text-xs text-gray-600 bg-gray-800/50 px-2 py-1 rounded">
          {document.file_type.toUpperCase()}
        </span>
        <span className="text-xs text-gray-600">
          {formatFileSize(document.file_size)}
        </span>
      </div>
    </div>
  );
}
