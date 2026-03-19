import { useCallback, useState, useRef } from "react";
import { Upload, FileUp, AlertCircle } from "lucide-react";

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/tiff",
  "image/webp",
];
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB

interface UploadAreaProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
}

export function UploadArea({ onUpload, isUploading = false }: UploadAreaProps) {
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

      onUpload(file);
    },
    [onUpload],
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

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragOver
            ? "border-blue-500 bg-blue-500/5"
            : "border-gray-700 hover:border-gray-600 bg-gray-900/30"
        } ${isUploading ? "opacity-50 pointer-events-none" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.webp"
          onChange={handleChange}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-3">
          {isUploading ? (
            <FileUp className="w-10 h-10 text-blue-400 animate-bounce" />
          ) : (
            <Upload className="w-10 h-10 text-gray-500" />
          )}
          <div>
            <p className="text-white font-medium">
              {isUploading ? "Uploading..." : "Drop a document here or click to browse"}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              PDF, PNG, JPG, TIFF, WebP — up to 20MB
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-400 mt-3">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}
    </div>
  );
}
