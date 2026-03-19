import { FileText } from "lucide-react";
import type { Citation } from "@/types/api";

interface CitationBlockProps {
  citation: Citation;
  onClick?: () => void;
}

export function CitationBlock({ citation, onClick }: CitationBlockProps) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center gap-1.5 text-xs bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded px-2 py-1 text-blue-300 transition-colors"
    >
      <FileText className="w-3 h-3" />
      <span>p.{citation.page}</span>
      {citation.text_span && (
        <span className="text-blue-400/70 truncate max-w-[120px]">
          {citation.text_span}
        </span>
      )}
    </button>
  );
}
