import { useState, useCallback, useRef } from "react";
import {
  FileText, Plus, MessageSquare, Trash2, ChevronDown,
  Upload, Loader2, AlertCircle, Clock, CheckCircle, RefreshCw,
} from "lucide-react";
import { toast } from "sonner";
import { useProjectDocuments, useAddProjectDocument, useRemoveProjectDocument } from "@/hooks/useProjects";
import { useProjectConversations, useDeleteConversation } from "@/hooks/useProjects";
import type { ProjectDocumentResponse, ConversationResponse } from "@/types/api";

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/tiff",
  "image/webp",
];
const MAX_FILE_SIZE = 20 * 1024 * 1024;

interface UploadEntry {
  name: string;
  progress: number;
  status: "uploading" | "indexing" | "ready";
}

const docStatusConfig: Record<string, { icon: React.ReactNode; className: string }> = {
  uploaded: { icon: <Clock className="w-3 h-3" />, className: "bg-gray-800 text-gray-300" },
  processing: { icon: <Loader2 className="w-3 h-3 animate-spin" />, className: "bg-amber-900/50 text-amber-300" },
  ready: { icon: <CheckCircle className="w-3 h-3" />, className: "bg-emerald-900/50 text-emerald-300" },
  error: { icon: <AlertCircle className="w-3 h-3" />, className: "bg-red-900/50 text-red-300" },
};

interface ProjectSidebarProps {
  projectId: string;
  activeConvId: string | null;
  onSelectConversation: (convId: string) => void;
  onNewChat: () => void;
}

export function ProjectSidebar({ projectId, activeConvId, onSelectConversation, onNewChat }: ProjectSidebarProps) {
  const { data: documents, isLoading: docsLoading } = useProjectDocuments(projectId);
  const addDoc = useAddProjectDocument(projectId);
  const removeDoc = useRemoveProjectDocument(projectId);
  const { data: conversations } = useProjectConversations(projectId);
  const deleteConv = useDeleteConversation(projectId);

  const [docsOpen, setDocsOpen] = useState(true);
  const [convsOpen, setConvsOpen] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingFiles, setUploadingFiles] = useState<Map<string, UploadEntry>>(new Map());
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndUpload = useCallback(
    (file: File) => {
      setError(null);
      if (!ACCEPTED_TYPES.includes(file.type)) {
        setError("Unsupported file type. Use PDF, PNG, JPG, TIFF, or WebP.");
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        setError("File too large. Maximum size is 20MB.");
        return;
      }

      const uploadId = `upload-${Date.now()}-${file.name}`;

      setUploadingFiles((prev) => {
        const next = new Map(prev);
        next.set(uploadId, { name: file.name, progress: 0, status: "uploading" });
        return next;
      });

      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadingFiles((prev) => {
          const entry = prev.get(uploadId);
          if (!entry || entry.status !== "uploading") {
            clearInterval(progressInterval);
            return prev;
          }
          const next = new Map(prev);
          const newProgress = Math.min(entry.progress + Math.random() * 25 + 10, 90);
          next.set(uploadId, { ...entry, progress: newProgress });
          return next;
        });
      }, 300);

      addDoc.mutate(file, {
        onSuccess: () => {
          clearInterval(progressInterval);
          // Move to indexing
          setUploadingFiles((prev) => {
            const next = new Map(prev);
            next.set(uploadId, { name: file.name, progress: 100, status: "indexing" });
            return next;
          });
          // Remove after indexing simulation
          setTimeout(() => {
            setUploadingFiles((prev) => {
              const next = new Map(prev);
              next.delete(uploadId);
              return next;
            });
          }, 5000);
        },
        onError: () => {
          clearInterval(progressInterval);
          setUploadingFiles((prev) => {
            const next = new Map(prev);
            next.delete(uploadId);
            return next;
          });
          setError("Upload failed. Please try again.");
        },
      });
    },
    [addDoc],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      for (const file of files) {
        validateAndUpload(file);
      }
    },
    [validateAndUpload],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files) {
        Array.from(files).forEach((file) => validateAndUpload(file));
      }
      if (inputRef.current) inputRef.current.value = "";
    },
    [validateAndUpload],
  );

  const handleRemoveDoc = (docId: string, filename: string) => {
    const msg = `Delete "${filename}"?\n\nThis permanently removes the document, its extracted data, and all indexed chunks. This cannot be undone.`;
    if (window.confirm(msg)) {
      removeDoc.mutate(docId);
    }
  };

  const handleDeleteConversation = (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteConv.mutate(convId, {
      onSuccess: () => {
        if (activeConvId === convId) {
          onNewChat();
        }
      },
    });
  };

  const convList = conversations ?? [];
  const docList = documents ?? [];
  const uploadEntries = Array.from(uploadingFiles.entries());

  return (
    <div
      className="w-[280px] flex-shrink-0 border-r border-[#1e1e2e] bg-[#12121a]/50 flex flex-col h-full"
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={(e) => {
        if (e.currentTarget.contains(e.relatedTarget as Node)) return;
        setIsDragOver(false);
      }}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-10 bg-indigo-500/10 border-2 border-dashed border-indigo-500 rounded-lg flex items-center justify-center pointer-events-none">
          <div className="text-center">
            <Upload className="w-8 h-8 text-indigo-400 mx-auto mb-2" />
            <p className="text-sm text-indigo-300 font-medium">Drop files to upload</p>
          </div>
        </div>
      )}

      {/* Documents section */}
      <div className="flex flex-col min-h-0 flex-1">
        <button
          onClick={() => setDocsOpen(!docsOpen)}
          className="flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:bg-white/5 transition-colors"
        >
          <span>Documents {docList.length > 0 && `(${docList.length})`}</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${docsOpen ? "" : "-rotate-90"}`} />
        </button>

        {docsOpen && (
          <div className="flex-1 overflow-y-auto min-h-0">
            {docsLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
              </div>
            ) : docList.length === 0 && uploadEntries.length === 0 ? (
              <div className="text-center py-6 px-4">
                <FileText className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                <p className="text-xs text-gray-500">No documents yet</p>
              </div>
            ) : (
              <div className="px-2 space-y-0.5">
                {/* Uploading files */}
                {uploadEntries.map(([id, entry]) => (
                  <div key={id} className="px-2 py-2 rounded-lg bg-[#1a1a25]/50">
                    <div className="flex items-center gap-2">
                      <FileText className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                      <span className="text-xs text-white truncate flex-1">{entry.name}</span>
                      {entry.status === "indexing" && (
                        <span className="text-[10px] text-amber-400 animate-pulse whitespace-nowrap">Indexing...</span>
                      )}
                    </div>
                    {entry.status === "uploading" && (
                      <div className="mt-1.5 h-1 bg-[#1e1e2e] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                          style={{ width: `${entry.progress}%` }}
                        />
                      </div>
                    )}
                    {entry.status === "indexing" && (
                      <div className="mt-1.5 h-1 bg-[#1e1e2e] rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500 rounded-full animate-pulse w-full" />
                      </div>
                    )}
                  </div>
                ))}

                {/* Existing documents */}
                {docList.map((doc: ProjectDocumentResponse) => {
                  const status = docStatusConfig[doc.status] ?? docStatusConfig.uploaded;
                  return (
                    <div
                      key={doc.id}
                      className="group flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-white/5 transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-white truncate">{doc.filename}</p>
                      </div>
                      <span className={`inline-flex items-center gap-0.5 text-[9px] font-medium px-1.5 py-0.5 rounded-full ${status.className}`}>
                        {status.icon}
                      </span>
                      <button
                        onClick={async () => {
                          try {
                            toast.loading("Re-indexing...", { id: `reindex-${doc.id}` });
                            const { useAuthStore } = await import("@/stores/auth-store");
                            const token = useAuthStore.getState().accessToken;
                            const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
                            const resp = await fetch(
                              `${BASE_URL}/api/v1/projects/${projectId}/documents/${doc.id}/reindex`,
                              { method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {} },
                            );
                            if (!resp.ok) throw new Error("Reindex failed");
                            const result = await resp.json();
                            toast.success(`Re-indexed: ${result.chunks_created} chunks`, { id: `reindex-${doc.id}` });
                          } catch (e) {
                            toast.error(`Reindex failed`, { id: `reindex-${doc.id}` });
                          }
                        }}
                        className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-indigo-500/10 text-gray-600 hover:text-indigo-400 transition-all"
                        aria-label="Re-index document"
                        title="Re-index RAG chunks"
                      >
                        <RefreshCw className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => handleRemoveDoc(doc.id, doc.filename)}
                        className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-red-500/10 text-gray-600 hover:text-red-400 transition-all"
                        aria-label="Remove document"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Upload button */}
            <div className="px-3 py-2">
              <input
                ref={inputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.tiff,.webp"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />
              <button
                onClick={() => inputRef.current?.click()}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white border border-dashed border-[#2a2a3a] hover:border-indigo-500/50 rounded-lg transition-colors hover:bg-indigo-500/5"
              >
                <Plus className="w-3.5 h-3.5" />
                Upload Document
              </button>
              {error && (
                <div className="flex items-center gap-1.5 text-[10px] text-red-400 mt-1.5">
                  <AlertCircle className="w-3 h-3 flex-shrink-0" />
                  {error}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Divider */}
      <div className="border-t border-[#1e1e2e]" />

      {/* Conversations section */}
      <div className="flex flex-col min-h-0 flex-1">
        <button
          onClick={() => setConvsOpen(!convsOpen)}
          className="flex items-center justify-between px-4 py-2.5 text-xs font-semibold text-gray-400 uppercase tracking-wider hover:bg-white/5 transition-colors"
        >
          <span>Conversations {convList.length > 0 && `(${convList.length})`}</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform ${convsOpen ? "" : "-rotate-90"}`} />
        </button>

        {convsOpen && (
          <div className="flex-1 overflow-y-auto min-h-0">
            {convList.length === 0 ? (
              <div className="text-center py-6 px-4">
                <MessageSquare className="w-8 h-8 text-gray-700 mx-auto mb-2" />
                <p className="text-xs text-gray-500">No conversations yet</p>
              </div>
            ) : (
              <div className="px-2 space-y-0.5">
                {convList.map((conv: ConversationResponse) => (
                  <div
                    key={conv.id}
                    onClick={() => onSelectConversation(conv.id)}
                    role="button"
                    tabIndex={0}
                    className={`group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors ${
                      activeConvId === conv.id
                        ? "bg-indigo-500/10 text-white"
                        : "text-gray-400 hover:bg-white/5 hover:text-gray-300"
                    }`}
                  >
                    <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="flex-1 text-xs truncate">{conv.title ?? "Untitled"}</span>
                    <button
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-all"
                      aria-label="Delete conversation"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {/* New chat button */}
            <div className="px-3 py-2">
              <button
                onClick={onNewChat}
                className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-white bg-indigo-600/10 hover:bg-indigo-600 border border-indigo-500/20 hover:border-indigo-500 rounded-lg transition-colors"
              >
                <Plus className="w-3.5 h-3.5" />
                New Chat
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
