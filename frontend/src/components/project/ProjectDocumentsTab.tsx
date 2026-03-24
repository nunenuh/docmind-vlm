import { useState, useRef, useCallback } from "react";
import {
  FileText, Upload, Trash2, RefreshCw, Loader2, AlertCircle,
  CheckCircle, Clock, Plus, Image,
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
}

function formatSize(bytes: number): string {
  if (!bytes || bytes <= 0) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Upload lifecycle per file
interface UploadTask {
  id: string;
  filename: string;
  fileSize: number;
  fileType: string;
  step: "uploading" | "linking" | "indexing" | "done" | "error";
  stepLabel: string;
  progress: number; // 0-100
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
    setUploadTasks((prev) => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
  };

  const handleUploadFile = useCallback(
    async (file: File) => {
      if (file.size > MAX_SIZE) {
        toast.error(`${file.name} exceeds 20MB limit`);
        return;
      }

      const taskId = `upload-${Date.now()}-${file.name}`;

      // Add task
      setUploadTasks((prev) => {
        const next = new Map(prev);
        next.set(taskId, {
          id: taskId,
          filename: file.name,
          fileSize: file.size,
          fileType: file.name.split(".").pop()?.toLowerCase() || "pdf",
          step: "uploading",
          stepLabel: "Uploading file...",
          progress: 10,
        });
        return next;
      });

      try {
        // Step 1: Upload + link to project (addDocumentToProject does both)
        updateTask(taskId, { step: "uploading", stepLabel: "Uploading to storage...", progress: 20 });
        await new Promise((r) => setTimeout(r, 500));
        updateTask(taskId, { step: "linking", stepLabel: "Linking to project & indexing...", progress: 45 });

        await addDocumentToProject(projectId, file);

        // Step 2: Indexing happens on backend during addDocumentToProject
        updateTask(taskId, { step: "indexing", stepLabel: "RAG indexing in progress...", progress: 70 });

        // Refresh document list immediately so it shows
        queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });

        await new Promise((r) => setTimeout(r, 2000));
        updateTask(taskId, { progress: 90, stepLabel: "Finalizing..." });
        await new Promise((r) => setTimeout(r, 1000));

        // Step 3: Done
        updateTask(taskId, { step: "done", stepLabel: "Uploaded & indexed", progress: 100 });

        // Refresh again to get final status
        queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });
        queryClient.invalidateQueries({ queryKey: ["projects"] });

        // Remove task after 3 seconds
        setTimeout(() => removeTask(taskId), 3000);

      } catch (e) {
        updateTask(taskId, {
          step: "error",
          stepLabel: `Failed: ${(e as Error).message}`,
          progress: 0,
          error: (e as Error).message,
        });
      }
    },
    [projectId, queryClient],
  );

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      Array.from(files).forEach((file) => handleUploadFile(file));
    },
    [handleUploadFile],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const handleReindex = async (docId: string, filename: string) => {
    const taskId = `reindex-${docId}`;
    setUploadTasks((prev) => {
      const next = new Map(prev);
      next.set(taskId, {
        id: taskId, filename, fileSize: 0, fileType: "pdf",
        step: "indexing", stepLabel: "Re-indexing chunks...", progress: 50,
      });
      return next;
    });

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
      const resp = await fetch(
        `${BASE_URL}/api/v1/projects/${projectId}/documents/${docId}/reindex`,
        { method: "POST", headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {} },
      );
      if (!resp.ok) throw new Error("Reindex failed");
      const result = await resp.json();
      updateTask(taskId, { step: "done", stepLabel: `Re-indexed: ${result.chunks_created} chunks`, progress: 100 });
      queryClient.invalidateQueries({ queryKey: ["project-documents", projectId] });
      setTimeout(() => removeTask(taskId), 3000);
    } catch (e) {
      updateTask(taskId, { step: "error", stepLabel: `Re-index failed`, progress: 0, error: (e as Error).message });
    }
  };

  const docList = docs ?? [];
  const activeTasks = Array.from(uploadTasks.values());

  return (
    <div className="h-full flex flex-col bg-[#0a0a0f]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e2e]">
        <h2 className="text-sm font-semibold text-white">Documents ({docList.length})</h2>
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
        ) : docList.length === 0 && activeTasks.length === 0 ? (
          <div
            className={`flex flex-col items-center justify-center py-16 border-2 border-dashed rounded-xl cursor-pointer transition-colors ${
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
            {/* Active upload/indexing tasks */}
            {activeTasks.map((task) => (
              <UploadProgressCard
                key={task.id}
                task={task}
                onRetry={() => removeTask(task.id)}
                onDismiss={() => removeTask(task.id)}
              />
            ))}

            {/* Existing documents */}
            {docList.map((doc: ProjectDocumentResponse) => (
              <DocumentCard
                key={doc.id}
                doc={doc}
                onReindex={() => handleReindex(doc.id, doc.filename)}
                onRemove={() => {
                  if (window.confirm(`Remove "${doc.filename}"?`)) removeDoc.mutate(doc.id);
                }}
              />
            ))}

            {/* Drop zone at bottom */}
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


function UploadProgressCard({
  task,
  onRetry,
  onDismiss,
}: {
  task: UploadTask;
  onRetry: () => void;
  onDismiss: () => void;
}) {
  const isError = task.step === "error";
  const isDone = task.step === "done";

  return (
    <div className={`px-4 py-3 rounded-xl border transition-colors ${
      isError ? "bg-rose-500/5 border-rose-500/20" :
      isDone ? "bg-emerald-500/5 border-emerald-500/20" :
      "bg-indigo-500/5 border-indigo-500/20"
    }`}>
      <div className="flex items-center gap-3 mb-2">
        {/* Icon */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isError ? "bg-rose-500/10" : isDone ? "bg-emerald-500/10" : "bg-indigo-500/10"
        }`}>
          {isError ? <AlertCircle className="w-4 h-4 text-rose-400" /> :
           isDone ? <CheckCircle className="w-4 h-4 text-emerald-400" /> :
           <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm text-white font-medium truncate">{task.filename}</p>
          <p className={`text-xs mt-0.5 ${
            isError ? "text-rose-400" : isDone ? "text-emerald-400" : "text-indigo-300"
          }`}>
            {task.stepLabel}
          </p>
        </div>

        {/* Size */}
        {task.fileSize > 0 && (
          <span className="text-xs text-gray-500">{formatSize(task.fileSize)}</span>
        )}

        {/* Actions */}
        {isError && (
          <button onClick={onRetry} className="text-xs text-rose-400 hover:text-rose-300 px-2 py-1 rounded hover:bg-rose-500/10">
            Dismiss
          </button>
        )}
        {isDone && (
          <button onClick={onDismiss} className="text-xs text-gray-500 hover:text-gray-300">
            ✕
          </button>
        )}
      </div>

      {/* Progress bar */}
      {!isDone && !isError && (
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-[#1a1a25] rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full bg-indigo-500 rounded-full transition-all duration-700 ease-out"
              style={{ width: `${task.progress}%` }}
            />
          </div>
          <span className="text-[10px] text-gray-500 tabular-nums w-8 text-right">{task.progress}%</span>
        </div>
      )}

      {/* Step indicators */}
      {!isDone && !isError && (
        <div className="flex items-center gap-4 mt-2">
          <StepDot label="Upload" active={task.step === "uploading"} done={["linking", "indexing", "done"].includes(task.step)} />
          <StepLine done={["linking", "indexing", "done"].includes(task.step)} />
          <StepDot label="Link" active={task.step === "linking"} done={["indexing", "done"].includes(task.step)} />
          <StepLine done={["indexing", "done"].includes(task.step)} />
          <StepDot label="Index" active={task.step === "indexing"} done={task.step === "done"} />
        </div>
      )}
    </div>
  );
}

function StepDot({ label, active, done }: { label: string; active: boolean; done: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={`w-2 h-2 rounded-full transition-colors ${
        done ? "bg-emerald-400" : active ? "bg-indigo-400 animate-pulse" : "bg-gray-700"
      }`} />
      <span className={`text-[10px] ${
        done ? "text-emerald-400" : active ? "text-indigo-300 font-medium" : "text-gray-600"
      }`}>{label}</span>
    </div>
  );
}

function StepLine({ done }: { done: boolean }) {
  return <div className={`flex-1 h-px max-w-8 ${done ? "bg-emerald-500/30" : "bg-gray-800"}`} />;
}

function DocumentCard({
  doc,
  onReindex,
  onRemove,
}: {
  doc: ProjectDocumentResponse;
  onReindex: () => void;
  onRemove: () => void;
}) {
  const isImage = ["png", "jpg", "jpeg", "webp", "tiff"].includes(doc.file_type);
  const statusCfg = {
    uploaded: { icon: <Clock className="w-3.5 h-3.5" />, label: "Uploaded", color: "text-gray-400", bg: "bg-gray-500/10" },
    processing: { icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />, label: "Processing", color: "text-indigo-400", bg: "bg-indigo-500/10" },
    ready: { icon: <CheckCircle className="w-3.5 h-3.5" />, label: "Indexed", color: "text-emerald-400", bg: "bg-emerald-500/10" },
    error: { icon: <AlertCircle className="w-3.5 h-3.5" />, label: "Error", color: "text-rose-400", bg: "bg-rose-500/10" },
  };
  const status = statusCfg[doc.status as keyof typeof statusCfg] || statusCfg.uploaded;

  return (
    <div className="group flex items-center gap-4 px-4 py-3 bg-[#12121a] border border-[#1e1e2e] rounded-xl hover:border-[#2a2a3a] transition-colors">
      {/* Icon */}
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
        isImage ? "bg-emerald-500/10" : "bg-rose-500/10"
      }`}>
        {isImage ? <Image className="w-5 h-5 text-emerald-400" /> : <FileText className="w-5 h-5 text-rose-400" />}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-white font-medium truncate">{doc.filename}</p>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-xs text-gray-500">{doc.file_type.toUpperCase()}</span>
          {doc.file_size > 0 && <span className="text-xs text-gray-600">{formatSize(doc.file_size)}</span>}
          {doc.page_count > 0 && <span className="text-xs text-gray-600">{doc.page_count} pages</span>}
        </div>
      </div>

      {/* Status badge */}
      <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${status.color} ${status.bg}`}>
        {status.icon}
        {status.label}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onReindex}
          className="p-2 text-gray-500 hover:text-indigo-400 rounded-lg hover:bg-indigo-500/10 transition-colors"
          title="Re-index"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
        <button
          onClick={onRemove}
          className="p-2 text-gray-500 hover:text-rose-400 rounded-lg hover:bg-rose-500/10 transition-colors"
          title="Remove"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
