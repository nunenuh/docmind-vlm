import { useState, useRef, useCallback } from "react";
import {
  FileText, Upload, Trash2, RefreshCw, Loader2, AlertCircle,
  CheckCircle, Clock, Plus, Image, MoreHorizontal, X,
} from "lucide-react";
import { toast } from "sonner";
import {
  useProjectDocuments,
  useRemoveProjectDocument,
} from "@/hooks/useProjects";
import { useAuthStore } from "@/stores/auth-store";
import { addDocumentToProject } from "@/lib/api";
import { useQueryClient } from "@tanstack/react-query";
import type { ProjectDocumentResponse } from "@/types/api";

const ACCEPTED = ".pdf,.png,.jpg,.jpeg,.tiff,.webp";
const MAX_SIZE = 20 * 1024 * 1024;

interface Props {
  projectId: string;
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
  fileSize: number;
  fileType: string;
  step: "uploading" | "linking" | "indexing" | "done" | "error";
  stepLabel: string;
  progress: number;
  error?: string;
}

export function ProjectDocumentsTab({ projectId }: Props) {
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
          id: taskId, filename: file.name, fileSize: file.size,
          fileType: file.name.split(".").pop()?.toLowerCase() || "pdf",
          step: "uploading", stepLabel: "Uploading...", progress: 15,
        });
        return next;
      });

      try {
        updateTask(taskId, { step: "uploading", stepLabel: "Uploading to storage...", progress: 25 });
        await new Promise((r) => setTimeout(r, 300));
        updateTask(taskId, { step: "linking", stepLabel: "Linking to project...", progress: 45 });

        await addDocumentToProject(projectId, file);

        updateTask(taskId, { step: "indexing", stepLabel: "Indexing for RAG...", progress: 70 });
        queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });

        await new Promise((r) => setTimeout(r, 2000));
        updateTask(taskId, { progress: 90, stepLabel: "Finalizing..." });
        await new Promise((r) => setTimeout(r, 1000));

        updateTask(taskId, { step: "done", stepLabel: "Complete", progress: 100 });
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
      n.set(taskId, { id: taskId, filename, fileSize: 0, fileType: "pdf", step: "indexing", stepLabel: "Re-indexing...", progress: 50 });
      return n;
    });
    try {
      const token = useAuthStore.getState().accessToken;
      const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
      const resp = await fetch(`${BASE_URL}/api/v1/projects/${projectId}/documents/${docId}/reindex`, {
        method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {},
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
    <div className="h-full flex flex-col bg-[#0C0D12]">
      {/* Subheader */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-white/[0.04]">
        <div className="flex items-center gap-3">
          <p className="text-[13px] font-semibold text-gray-200 tracking-tight">
            {docList.length} document{docList.length !== 1 ? "s" : ""}
          </p>
          {docList.length > 0 && (
            <span className="text-[11px] text-gray-600">
              {formatSize(docList.reduce((sum, d) => sum + (d.file_size || 0), 0))} total
            </span>
          )}
        </div>
        <button
          onClick={() => inputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-[12px] font-semibold rounded-lg transition-all duration-200 shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 active:scale-[0.98]"
        >
          <Plus className="w-3.5 h-3.5" />
          Upload Files
        </button>
        <input ref={inputRef} type="file" accept={ACCEPTED} multiple
          onChange={(e) => { if (e.target.files) handleFiles(e.target.files); e.target.value = ""; }}
          className="hidden" />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-5">
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
            </div>
          ) : docList.length === 0 && activeTasks.length === 0 ? (
            /* Empty state */
            <div
              className={`flex flex-col items-center justify-center py-20 rounded-2xl border-2 border-dashed cursor-pointer transition-all duration-300 ${
                dragOver
                  ? "border-indigo-500/50 bg-indigo-500/[0.03] scale-[1.01]"
                  : "border-white/[0.06] hover:border-white/[0.12]"
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/10 flex items-center justify-center mb-5">
                <Upload className="w-6 h-6 text-indigo-400" />
              </div>
              <p className="text-sm font-medium text-gray-300 mb-1">Drop files here or click to upload</p>
              <p className="text-xs text-gray-600">PDF, PNG, JPG, TIFF, WebP — up to 20MB each</p>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Active upload tasks */}
              {activeTasks.map((task) => (
                <UploadCard key={task.id} task={task} onDismiss={() => removeTask(task.id)} />
              ))}

              {/* Existing documents */}
              {docList.map((doc: ProjectDocumentResponse, i: number) => (
                <DocumentRow
                  key={doc.id}
                  doc={doc}
                  index={i}
                  onReindex={() => handleReindex(doc.id, doc.filename)}
                  onRemove={() => {
                    const msg = `Delete "${doc.filename}"?\n\nThis permanently removes the document, its extracted data, and all indexed chunks. This cannot be undone.`;
                    if (window.confirm(msg)) removeDoc.mutate(doc.id);
                  }}
                />
              ))}

              {/* Upload more zone */}
              <div
                className={`flex items-center justify-center py-5 rounded-xl border border-dashed cursor-pointer transition-all duration-200 mt-3 ${
                  dragOver ? "border-indigo-500/40 bg-indigo-500/[0.02]" : "border-white/[0.06] hover:border-white/[0.1]"
                }`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
              >
                <span className="flex items-center gap-2 text-[11px] text-gray-600 hover:text-gray-400 transition-colors">
                  <Upload className="w-3.5 h-3.5" />
                  Drop more files or click to upload
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Upload Progress Card ──────────────────────────────── */

function UploadCard({ task, onDismiss }: { task: UploadTask; onDismiss: () => void }) {
  const isError = task.step === "error";
  const isDone = task.step === "done";

  const colors = isError
    ? { bg: "bg-rose-500/[0.04]", border: "border-rose-500/[0.12]", bar: "bg-rose-500", text: "text-rose-400" }
    : isDone
    ? { bg: "bg-emerald-500/[0.04]", border: "border-emerald-500/[0.12]", bar: "bg-emerald-500", text: "text-emerald-400" }
    : { bg: "bg-indigo-500/[0.04]", border: "border-indigo-500/[0.12]", bar: "bg-indigo-500", text: "text-indigo-300" };

  return (
    <div className={`${colors.bg} border ${colors.border} rounded-xl px-4 py-3 transition-all duration-300`}>
      <div className="flex items-center gap-3">
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isError ? "bg-rose-500/10" : isDone ? "bg-emerald-500/10" : "bg-indigo-500/10"
        }`}>
          {isError ? <AlertCircle className="w-4 h-4 text-rose-400" /> :
           isDone ? <CheckCircle className="w-4 h-4 text-emerald-400" /> :
           <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-[13px] text-gray-200 font-medium truncate">{task.filename}</p>
          <p className={`text-[11px] mt-0.5 ${colors.text}`}>{task.stepLabel}</p>
        </div>

        {task.fileSize > 0 && (
          <span className="text-[11px] text-gray-600 flex-shrink-0">{formatSize(task.fileSize)}</span>
        )}

        {(isDone || isError) && (
          <button onClick={onDismiss} className="text-gray-600 hover:text-gray-400 p-1 transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Progress bar */}
      {!isDone && !isError && (
        <div className="mt-2.5 flex items-center gap-3">
          <div className="flex-1 h-1 bg-white/[0.04] rounded-full overflow-hidden">
            <div
              className={`h-full ${colors.bar} rounded-full transition-all duration-700 ease-out`}
              style={{ width: `${task.progress}%` }}
            />
          </div>
          <span className="text-[10px] text-gray-600 tabular-nums w-7 text-right">{task.progress}%</span>
        </div>
      )}

      {/* Step indicators */}
      {!isDone && !isError && (
        <div className="flex items-center gap-3 mt-2">
          <StepPill label="Upload" active={task.step === "uploading"} done={["linking", "indexing", "done"].includes(task.step)} />
          <div className={`flex-1 h-px max-w-6 ${["linking", "indexing", "done"].includes(task.step) ? "bg-emerald-500/20" : "bg-white/[0.04]"}`} />
          <StepPill label="Link" active={task.step === "linking"} done={["indexing", "done"].includes(task.step)} />
          <div className={`flex-1 h-px max-w-6 ${["indexing", "done"].includes(task.step) ? "bg-emerald-500/20" : "bg-white/[0.04]"}`} />
          <StepPill label="Index" active={task.step === "indexing"} done={task.step === "done"} />
        </div>
      )}
    </div>
  );
}

function StepPill({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full transition-colors ${
      done ? "bg-emerald-500/10 text-emerald-400" :
      active ? "bg-indigo-500/10 text-indigo-300" :
      "bg-white/[0.02] text-gray-600"
    }`}>
      {label}
    </span>
  );
}

/* ── Document Row ──────────────────────────────────────── */

function DocumentRow({
  doc, index, onReindex, onRemove,
}: {
  doc: ProjectDocumentResponse;
  index: number;
  onReindex: () => void;
  onRemove: () => void;
}) {
  const isImage = ["png", "jpg", "jpeg", "webp", "tiff"].includes(doc.file_type);
  const [showMenu, setShowMenu] = useState(false);

  const statusMap: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
    uploaded: { label: "Uploaded", color: "text-amber-400 bg-amber-500/[0.08] border-amber-500/[0.12]", icon: <Clock className="w-3 h-3" /> },
    processing: { label: "Processing", color: "text-indigo-400 bg-indigo-500/[0.08] border-indigo-500/[0.12]", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    ready: { label: "Indexed", color: "text-emerald-400 bg-emerald-500/[0.08] border-emerald-500/[0.12]", icon: <CheckCircle className="w-3 h-3" /> },
    error: { label: "Error", color: "text-rose-400 bg-rose-500/[0.08] border-rose-500/[0.12]", icon: <AlertCircle className="w-3 h-3" /> },
  };
  const status = statusMap[doc.status] || statusMap.uploaded;

  return (
    <div
      className="group flex items-center gap-4 px-4 py-3 rounded-xl border border-white/[0.04] hover:border-white/[0.08] bg-white/[0.01] hover:bg-white/[0.02] transition-all duration-200"
      style={{ animationDelay: `${index * 30}ms` }}
    >
      {/* File icon */}
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
        isImage ? "bg-emerald-500/[0.08] border border-emerald-500/[0.08]" : "bg-rose-500/[0.08] border border-rose-500/[0.08]"
      }`}>
        {isImage
          ? <Image className="w-4 h-4 text-emerald-400" />
          : <FileText className="w-4 h-4 text-rose-400" />}
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-[13px] text-gray-200 font-medium truncate tracking-tight">{doc.filename}</p>
        <div className="flex items-center gap-2.5 mt-0.5">
          <span className="text-[11px] text-gray-500 font-medium">{doc.file_type.toUpperCase()}</span>
          {doc.file_size > 0 && (
            <>
              <span className="text-[11px] text-gray-700">·</span>
              <span className="text-[11px] text-gray-600">{formatSize(doc.file_size)}</span>
            </>
          )}
          {doc.page_count > 0 && (
            <>
              <span className="text-[11px] text-gray-700">·</span>
              <span className="text-[11px] text-gray-600">{doc.page_count} pages</span>
            </>
          )}
        </div>
      </div>

      {/* Status badge */}
      <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium ${status.color}`}>
        {status.icon}
        {status.label}
      </div>

      {/* Actions menu */}
      <div className="relative">
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="p-1.5 text-gray-600 opacity-0 group-hover:opacity-100 hover:text-gray-300 rounded-lg hover:bg-white/[0.06] transition-all duration-200"
        >
          <MoreHorizontal className="w-4 h-4" />
        </button>

        {showMenu && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setShowMenu(false)} />
            <div className="absolute right-0 top-full mt-1 z-50 bg-[#16181F] border border-white/[0.08] rounded-lg shadow-2xl shadow-black/50 py-1 w-40">
              <button
                onClick={() => { setShowMenu(false); onReindex(); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-[12px] text-gray-300 hover:bg-white/[0.04] transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5 text-indigo-400" />
                Re-index
              </button>
              <button
                onClick={() => { setShowMenu(false); onRemove(); }}
                className="w-full flex items-center gap-2 px-3 py-2 text-[12px] text-rose-400 hover:bg-rose-500/[0.06] transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
