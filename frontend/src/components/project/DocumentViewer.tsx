import { useState, useEffect } from "react";
import { FileText, Loader2, AlertCircle, Image, ExternalLink } from "lucide-react";
import { supabase } from "@/lib/supabase";

interface Props {
  documentId: string;
  filename: string;
  fileType: string;
}

export function DocumentViewer({ documentId, filename, fileType }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isPdf = fileType === "pdf";
  const isImage = ["png", "jpg", "jpeg", "webp", "tiff"].includes(fileType);

  useEffect(() => {
    let cancelled = false;

    async function fetchUrl() {
      setLoading(true);
      setError(null);
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
        const resp = await fetch(`${BASE_URL}/api/v1/documents/${documentId}/url`, {
          headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
        });
        if (!resp.ok) throw new Error("Failed to get document URL");
        const data = await resp.json();
        if (!cancelled) setUrl(data.url);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchUrl();
    return () => { cancelled = true; };
  }, [documentId]);

  if (loading) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 bg-[#0B0D11]">
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
        <p className="text-[12px] text-gray-500">Loading document...</p>
      </div>
    );
  }

  if (error || !url) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-3 bg-[#0B0D11]">
        <div className="w-12 h-12 rounded-xl bg-rose-500/10 flex items-center justify-center">
          <AlertCircle className="w-5 h-5 text-rose-400" />
        </div>
        <p className="text-[13px] text-gray-300 font-medium">Cannot load document</p>
        <p className="text-[11px] text-gray-600">{error || "URL not available"}</p>
      </div>
    );
  }

  if (isPdf) {
    return (
      <div className="h-full flex flex-col bg-[#0B0D11]">
        {/* PDF toolbar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[0.05] flex-shrink-0">
          <FileText className="w-3.5 h-3.5 text-rose-400" />
          <span className="text-[12px] text-gray-300 truncate flex-1">{filename}</span>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-300 rounded hover:bg-white/[0.04] transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Open
          </a>
        </div>
        {/* PDF embed */}
        <div className="flex-1">
          <iframe
            src={`${url}#toolbar=1&navpanes=0`}
            className="w-full h-full border-0"
            title={filename}
          />
        </div>
      </div>
    );
  }

  if (isImage) {
    return (
      <div className="h-full flex flex-col bg-[#0B0D11]">
        {/* Image toolbar */}
        <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[0.05] flex-shrink-0">
          <Image className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-[12px] text-gray-300 truncate flex-1">{filename}</span>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-2 py-1 text-[10px] text-gray-500 hover:text-gray-300 rounded hover:bg-white/[0.04] transition-colors"
          >
            <ExternalLink className="w-3 h-3" />
            Open
          </a>
        </div>
        {/* Image viewer */}
        <div className="flex-1 overflow-auto flex items-center justify-center p-4">
          <img
            src={url}
            alt={filename}
            className="max-w-full max-h-full object-contain rounded-lg"
          />
        </div>
      </div>
    );
  }

  // Unsupported type fallback
  return (
    <div className="h-full flex flex-col items-center justify-center gap-3 bg-[#0B0D11]">
      <div className="w-12 h-12 rounded-xl bg-gray-800 flex items-center justify-center">
        <FileText className="w-5 h-5 text-gray-500" />
      </div>
      <p className="text-[13px] text-gray-300 font-medium">{filename}</p>
      <p className="text-[11px] text-gray-600">Preview not available for .{fileType} files</p>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-3 py-1.5 text-[11px] text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/15 rounded-lg transition-colors"
      >
        <ExternalLink className="w-3 h-3" />
        Download
      </a>
    </div>
  );
}
