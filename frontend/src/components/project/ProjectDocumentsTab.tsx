import { useState, useRef, useCallback } from "react";
import {
  FileText, Upload, Trash2, RefreshCw, Loader2, AlertCircle,
  CheckCircle, Clock, Plus, HardDrive, Database, Image,
} from "lucide-react";
import { toast } from "sonner";
import {
  useProjectDocuments,
  useAddProjectDocument,
  useRemoveProjectDocument,
} from "@/hooks/useProjects";
import { supabase } from "@/lib/supabase";
import type { ProjectDocumentResponse } from "@/types/api";

const ACCEPTED = ".pdf,.png,.jpg,.jpeg,.tiff,.webp";
const MAX_SIZE = 20 * 1024 * 1024;

interface Props {
  projectId: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const STATUS_CONFIG = {
  uploaded: { icon: <Clock className="w-3.5 h-3.5" />, label: "Uploaded", color: "text-gray-400" },
  processing: { icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />, label: "Processing", color: "text-indigo-400" },
  ready: { icon: <CheckCircle className="w-3.5 h-3.5" />, label: "Indexed", color: "text-emerald-400" },
  error: { icon: <AlertCircle className="w-3.5 h-3.5" />, label: "Error", color: "text-rose-400" },
};

export function ProjectDocumentsTab({ projectId }: Props) {
  const { data: docs, isLoading } = useProjectDocuments(projectId);
  const addDoc = useAddProjectDocument(projectId);
  const removeDoc = useRemoveProjectDocument(projectId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      Array.from(files).forEach((file) => {
        if (file.size > MAX_SIZE) {
          toast.error(`${file.name} is too large (max 20MB)`);
          return;
        }
        addDoc.mutate(file);
      });
    },
    [addDoc],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const handleReindex = async (docId: string) => {
    try {
      toast.loading("Re-indexing...", { id: `reindex-${docId}` });
      const { data: { session } } = await supabase.auth.getSession();
      const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
      const resp = await fetch(
        `${BASE_URL}/api/v1/projects/${projectId}/documents/${docId}/reindex`,
        { method: "POST", headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {} },
      );
      if (!resp.ok) throw new Error("Reindex failed");
      const result = await resp.json();
      toast.success(`Re-indexed: ${result.chunks_created} chunks`, { id: `reindex-${docId}` });
    } catch {
      toast.error("Re-index failed", { id: `reindex-${docId}` });
    }
  };

  const docList = docs ?? [];

  return (
    <div className="h-full flex flex-col bg-[#0a0a0f]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e2e]">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-white">Documents ({docList.length})</h2>
        </div>
        <button
          onClick={() => inputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Upload Files
        </button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          multiple
          onChange={(e) => { if (e.target.files) handleFiles(e.target.files); e.target.value = ""; }}
          className="hidden"
        />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
        ) : docList.length === 0 ? (
          /* Empty state with drag-drop */
          <div
            className={`flex flex-col items-center justify-center py-16 border-2 border-dashed rounded-xl transition-colors ${
              dragOver ? "border-indigo-500 bg-indigo-500/5" : "border-[#2a2a3a]"
            }`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            <Upload className="w-10 h-10 text-gray-600 mb-4" />
            <p className="text-sm text-gray-400 font-medium">Drop files here or click to upload</p>
            <p className="text-xs text-gray-600 mt-1">PDF, PNG, JPG, TIFF, WebP — up to 20MB each</p>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Document list */}
            {docList.map((doc: ProjectDocumentResponse) => {
              const status = STATUS_CONFIG[doc.status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.uploaded;
              return (
                <div
                  key={doc.id}
                  className="group flex items-center gap-4 px-4 py-3 bg-[#12121a] border border-[#1e1e2e] rounded-xl hover:border-[#2a2a3a] transition-colors"
                >
                  {/* Icon */}
                  {["png", "jpg", "jpeg", "webp", "tiff"].includes(doc.file_type) ? (
                    <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                      <Image className="w-5 h-5 text-emerald-400" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-rose-500/10 flex items-center justify-center flex-shrink-0">
                      <FileText className="w-5 h-5 text-rose-400" />
                    </div>
                  )}

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white font-medium truncate">{doc.filename}</p>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-xs text-gray-500">{doc.file_type.toUpperCase()}</span>
                      {doc.file_size > 0 && (
                        <span className="text-xs text-gray-600">{formatSize(doc.file_size)}</span>
                      )}
                      {doc.page_count > 0 && (
                        <span className="text-xs text-gray-600">{doc.page_count} pages</span>
                      )}
                    </div>
                  </div>

                  {/* Status */}
                  <div className={`flex items-center gap-1.5 text-xs font-medium ${status.color}`}>
                    {status.icon}
                    {status.label}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleReindex(doc.id)}
                      className="p-2 text-gray-500 hover:text-indigo-400 rounded-lg hover:bg-indigo-500/10 transition-colors"
                      title="Re-index RAG chunks"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        if (window.confirm(`Remove "${doc.filename}"?`)) removeDoc.mutate(doc.id);
                      }}
                      className="p-2 text-gray-500 hover:text-rose-400 rounded-lg hover:bg-rose-500/10 transition-colors"
                      title="Remove document"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}

            {/* Drag-drop area at bottom */}
            <div
              className={`flex items-center justify-center py-4 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
                dragOver ? "border-indigo-500 bg-indigo-500/5" : "border-[#2a2a3a] hover:border-[#3a3a4a]"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <Upload className="w-3.5 h-3.5" />
                Drop more files or click to upload
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
