import { useState, useRef, useCallback } from "react";
import {
  FileText, Upload, Loader2, Image, Plus, X,
  AlertCircle, CheckCircle, RefreshCw, Trash2,
} from "lucide-react";
import { toast } from "sonner";
import {
  useProjectDocuments,
  useRemoveProjectDocument,
} from "@/hooks/useProjects";
import { supabase } from "@/lib/supabase";
import { addDocumentToProject } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import type { ProjectDocumentResponse } from "@/types/api";

const ACCEPTED = ".pdf,.png,.jpg,.jpeg,.tiff,.webp";
const MAX_SIZE = 20 * 1024 * 1024;

interface Props {
  projectId: string;
  onDocumentClick?: (doc: ProjectDocumentResponse) => void;
}

function formatSize(bytes: number): string {
  if (!bytes || bytes <= 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface UploadTask {
  id: string;
  filename: string;
  step: "uploading" | "linking" | "indexing" | "done" | "error";
  stepLabel: string;
  progress: number;
  error?: string;
}

export function ProjectDocumentsPanel({ projectId, onDocumentClick }: Props) {
  const queryClient = useQueryClient();
  const { data: docs, isLoading } = useProjectDocuments(projectId);
  const removeDoc = useRemoveProjectDocument(projectId);
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadTasks, setUploadTasks] = useState<Map<string, UploadTask>>(new Map());

  const updateTask = (id: string, updates: Partial<UploadTask>) => {
    setUploadTasks((prev) => {
      const next = new Map(prev);
      const existing = next.get(id);
      if (existing) next.set(id, { ...existing, ...updates });
      return next;
    });
  };

  const removeTask = (id: string) => {
    setUploadTasks((prev) => { const n = new Map(prev); n.delete(id); return n; });
  };

  const handleUploadFile = useCallback(
    async (file: File) => {
      if (file.size > MAX_SIZE) { toast.error(`${file.name} exceeds 20MB limit`); return; }

      const taskId = `upload-${Date.now()}-${file.name}`;
      setUploadTasks((prev) => {
        const next = new Map(prev);
        next.set(taskId, {
          id: taskId, filename: file.name,
          step: "uploading", stepLabel: "Uploading...", progress: 15,
        });
        return next;
      });

      try {
        updateTask(taskId, { step: "uploading", stepLabel: "Uploading...", progress: 25 });
        await new Promise((r) => setTimeout(r, 300));
        updateTask(taskId, { step: "linking", stepLabel: "Linking...", progress: 45 });

        await addDocumentToProject(projectId, file);

        updateTask(taskId, { step: "indexing", stepLabel: "Indexing...", progress: 70 });
        queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });

        await new Promise((r) => setTimeout(r, 2000));
        updateTask(taskId, { progress: 90, stepLabel: "Finalizing..." });
        await new Promise((r) => setTimeout(r, 1000));

        updateTask(taskId, { step: "done", stepLabel: "Done", progress: 100 });
        queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });
        queryClient.invalidateQueries({ queryKey: ["projects"] });
        setTimeout(() => removeTask(taskId), 2500);
      } catch (e) {
        updateTask(taskId, { step: "error", stepLabel: (e as Error).message, progress: 0, error: (e as Error).message });
      }
    },
    [projectId, queryClient],
  );

  const handleFiles = useCallback(
    (files: FileList | File[]) => { Array.from(files).forEach((f) => handleUploadFile(f)); },
    [handleUploadFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => { e.preventDefault(); setDragOver(false); if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files); },
    [handleFiles],
  );

  const handleReindex = async (docId: string, filename: string) => {
    const taskId = `reindex-${docId}`;
    setUploadTasks((prev) => {
      const n = new Map(prev);
      n.set(taskId, { id: taskId, filename, step: "indexing", stepLabel: "Re-indexing...", progress: 50 });
      return n;
    });
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
      const resp = await fetch(`${BASE_URL}/api/v1/projects/${projectId}/documents/${docId}/reindex`, {
        method: "POST", headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
      });
      if (!resp.ok) throw new Error("Reindex failed");
      const result = await resp.json();
      updateTask(taskId, { step: "done", stepLabel: `${result.chunks_created} chunks`, progress: 100 });
      queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });
      setTimeout(() => removeTask(taskId), 2500);
    } catch {
      updateTask(taskId, { step: "error", stepLabel: "Re-index failed", progress: 0 });
    }
  };

  const docList = docs ?? [];
  const activeTasks = Array.from(uploadTasks.values());

  return (
    <div className="h-full flex flex-col bg-[#0D0F14]">
      {/* Header */}
      <div className="px-3 py-3 border-b border-white/[0.05] flex items-center justify-between flex-shrink-0">
        <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.08em]">
          Documents
        </span>
        <button
          onClick={() => inputRef.current?.click()}
          className="flex items-center gap-1 px-2 py-1 text-[10px] font-semibold text-indigo-400 bg-indigo-500/[0.08] hover:bg-indigo-500/[0.12] rounded transition-colors"
        >
          <Plus className="w-3 h-3" />
          Upload
        </button>
        <input
          ref={inputRef} type="file" accept={ACCEPTED} multiple
          onChange={(e) => { if (e.target.files) handleFiles(e.target.files); e.target.value = ""; }}
          className="hidden"
        />
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto py-1 scrollbar-thin">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
          </div>
        ) : docList.length === 0 && activeTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 px-4 text-center">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/[0.06] border border-indigo-500/[0.08] flex items-center justify-center mb-3">
              <Upload className="w-4 h-4 text-indigo-400/60" />
            </div>
            <p className="text-[11px] text-gray-500 mb-1">No documents yet</p>
            <p className="text-[10px] text-gray-600">Upload files to start chatting</p>
          </div>
        ) : (
          <div className="px-2 space-y-0.5">
            {/* Active uploads */}
            {activeTasks.map((task) => (
              <CompactUploadCard key={task.id} task={task} onDismiss={() => removeTask(task.id)} />
            ))}

            {/* Existing documents */}
            {docList.map((doc: ProjectDocumentResponse, i: number) => (
              <CompactDocRow
                key={doc.id}
                doc={doc}
                index={i}
                onClick={() => onDocumentClick?.(doc)}
                onReindex={() => handleReindex(doc.id, doc.filename)}
                onRemove={() => { if (window.confirm(`Remove "${doc.filename}"?`)) removeDoc.mutate(doc.id); }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Drop zone footer */}
      <div
        className={`px-3 py-2 border-t border-white/[0.05] flex-shrink-0 ${dragOver ? "bg-indigo-500/[0.04]" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <div
          className={`flex items-center justify-center py-3 border border-dashed rounded-lg cursor-pointer transition-colors ${
            dragOver ? "border-indigo-500/30 bg-indigo-500/[0.04]" : "border-white/[0.06] hover:border-white/[0.1]"
          }`}
          onClick={() => inputRef.current?.click()}
        >
          <span className="text-[10px] text-gray-600">Drop files or click to upload</span>
        </div>
      </div>
    </div>
  );
}

/* ── Compact Upload Card ─────────────────────────────── */

function CompactUploadCard({ task, onDismiss }: { task: UploadTask; onDismiss: () => void }) {
  const isError = task.step === "error";
  const isDone = task.step === "done";

  return (
    <div className={`px-2.5 py-2 rounded-lg transition-all duration-300 ${
      isError ? "bg-rose-500/[0.04] border border-rose-500/[0.1]" :
      isDone ? "bg-emerald-500/[0.04] border border-emerald-500/[0.1]" :
      "bg-indigo-500/[0.03] border border-indigo-500/[0.08]"
    }`}>
      <div className="flex items-center gap-2">
        <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 ${
          isError ? "bg-rose-500/10" : isDone ? "bg-emerald-500/10" : "bg-indigo-500/[0.1]"
        }`}>
          {isError ? <AlertCircle className="w-3.5 h-3.5 text-rose-400" /> :
           isDone ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> :
           <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] text-gray-300 truncate">{task.filename}</p>
          <p className={`text-[10px] ${isError ? "text-rose-400" : isDone ? "text-emerald-400" : "text-indigo-400/70"}`}>
            {task.stepLabel}
          </p>
        </div>
        {(isDone || isError) && (
          <button onClick={onDismiss} className="text-gray-600 hover:text-gray-400 p-0.5">
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
      {/* Progress bar */}
      {!isDone && !isError && (
        <div className="mt-1.5 flex items-center gap-2">
          <div className="flex-1 h-1 bg-white/[0.04] rounded-full overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-700 ease-out animate-pulse"
              style={{ width: `${task.progress}%` }}
            />
          </div>
          <span className="text-[9px] text-indigo-400/70 tabular-nums">{task.progress}%</span>
        </div>
      )}
    </div>
  );
}

/* ── Compact Document Row ────────────────────────────── */

function CompactDocRow({
  doc, index, onClick, onReindex, onRemove,
}: {
  doc: ProjectDocumentResponse;
  index: number;
  onClick?: () => void;
  onReindex: () => void;
  onRemove: () => void;
}) {
  const isImage = ["png", "jpg", "jpeg", "webp", "tiff"].includes(doc.file_type);
  const [showActions, setShowActions] = useState(false);

  const statusDot = (() => {
    switch (doc.status) {
      case "ready": return "bg-emerald-400";
      case "processing": return "bg-indigo-400 animate-pulse";
      case "error": return "bg-rose-400";
      default: return "bg-amber-400";
    }
  })();

  return (
    <div
      className="group flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-white/[0.03] transition-colors cursor-pointer relative"
      style={{ animationDelay: `${index * 30}ms` }}
      onClick={onClick}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      {/* File icon */}
      <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 ${
        isImage ? "bg-emerald-500/[0.08]" : "bg-rose-500/[0.08]"
      }`}>
        {isImage
          ? <Image className="w-3.5 h-3.5 text-emerald-400" />
          : <FileText className="w-3.5 h-3.5 text-rose-400" />}
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-[12px] text-gray-300 truncate">{doc.filename}</p>
        <p className="text-[10px] text-gray-600">
          {doc.file_type.toUpperCase()}
          {doc.file_size > 0 && ` · ${formatSize(doc.file_size)}`}
          {doc.page_count > 0 && ` · ${doc.page_count}p`}
        </p>
      </div>

      {/* Status dot or action buttons */}
      {showActions ? (
        <div className="flex items-center gap-0.5 flex-shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); onReindex(); }}
            className="p-1 text-gray-600 hover:text-indigo-400 rounded transition-colors"
            title="Re-index"
          >
            <RefreshCw className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onRemove(); }}
            className="p-1 text-gray-600 hover:text-rose-400 rounded transition-colors"
            title="Remove"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      ) : (
        <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${statusDot}`} title={doc.status} />
      )}
    </div>
  );
}
