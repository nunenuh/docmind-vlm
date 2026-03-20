import { useCallback, useState, useRef } from "react";
import { Upload, FileUp, FileText, Trash2, AlertCircle, Loader2, Clock, CheckCircle } from "lucide-react";
import { useProjectDocuments, useAddProjectDocument, useRemoveProjectDocument } from "@/hooks/useProjects";
import type { ProjectDocumentResponse } from "@/types/api";

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/tiff",
  "image/webp",
];
const MAX_FILE_SIZE = 20 * 1024 * 1024;

const statusConfig: Record<string, { icon: React.ReactNode; className: string }> = {
  uploaded: { icon: <Clock className="w-3 h-3" />, className: "bg-gray-800 text-gray-300" },
  processing: { icon: <Loader2 className="w-3 h-3 animate-spin" />, className: "bg-blue-900/50 text-blue-300" },
  ready: { icon: <CheckCircle className="w-3 h-3" />, className: "bg-green-900/50 text-green-300" },
  error: { icon: <AlertCircle className="w-3 h-3" />, className: "bg-red-900/50 text-red-300" },
};

interface ProjectDocumentListProps {
  projectId: string;
}

export function ProjectDocumentList({ projectId }: ProjectDocumentListProps) {
  const { data: documents, isLoading } = useProjectDocuments(projectId);
  const addDoc = useAddProjectDocument(projectId);
  const removeDoc = useRemoveProjectDocument(projectId);

  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      addDoc.mutate(file);
    },
    [addDoc],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) validateAndUpload(file);
    },
    [validateAndUpload],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) validateAndUpload(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [validateAndUpload],
  );

  const handleRemove = (docId: string, filename: string) => {
    if (window.confirm(`Remove "${filename}" from this project?`)) {
      removeDoc.mutate(docId);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-sm font-semibold text-white mb-3">Documents</h2>

        {/* Upload area */}
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
            isDragOver
              ? "border-blue-500 bg-blue-500/5"
              : "border-gray-700 hover:border-gray-600 bg-gray-900/30"
          } ${addDoc.isPending ? "opacity-50 pointer-events-none" : ""}`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.webp"
            onChange={handleChange}
            className="hidden"
          />
          <div className="flex flex-col items-center gap-2">
            {addDoc.isPending ? (
              <FileUp className="w-6 h-6 text-blue-400 animate-bounce" />
            ) : (
              <Upload className="w-6 h-6 text-gray-500" />
            )}
            <p className="text-xs text-gray-400">
              {addDoc.isPending ? "Uploading..." : "Drop files or click to upload"}
            </p>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 text-xs text-red-400 mt-2">
            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
            {error}
          </div>
        )}
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
          </div>
        ) : !documents || documents.length === 0 ? (
          <div className="text-center py-12 px-4">
            <FileText className="w-10 h-10 text-gray-700 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No documents yet.</p>
            <p className="text-xs text-gray-600 mt-1">Upload files to get started.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800/50">
            {documents.map((doc: ProjectDocumentResponse) => {
              const status = statusConfig[doc.status] ?? statusConfig.uploaded;
              return (
                <div
                  key={doc.id}
                  className="group flex items-center gap-3 px-4 py-3 hover:bg-gray-900/30 transition-colors"
                >
                  <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-white truncate">{doc.filename}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${status.className}`}>
                        {status.icon}
                        {doc.status}
                      </span>
                      <span className="text-[10px] text-gray-600">{doc.file_type.toUpperCase()}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemove(doc.id, doc.filename)}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all"
                    aria-label="Remove document"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
