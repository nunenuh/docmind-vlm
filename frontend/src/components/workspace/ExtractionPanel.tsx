import { useState } from "react";
import { Code, Table2, Loader2, FileSearch, Download } from "lucide-react";
import { toast } from "sonner";
import { useAuthStore } from "@/stores/auth-store";
import { useExtraction } from "@/hooks/useExtraction";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface ExtractionPanelProps {
  documentId: string;
}

export function ExtractionPanel({ documentId }: ExtractionPanelProps) {
  const { data, isLoading } = useExtraction(documentId);
  const { selectedFieldId, selectField } = useWorkspaceStore();
  const [showJson, setShowJson] = useState(false);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
        <p className="text-xs text-gray-500 mt-3">Loading extraction data...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6">
        <div className="w-12 h-12 rounded-xl bg-gray-900 border border-gray-800 flex items-center justify-center mb-4">
          <FileSearch className="w-6 h-6 text-gray-700" />
        </div>
        <p className="text-sm font-medium text-gray-400 mb-1">No extraction data</p>
        <p className="text-xs text-gray-600 text-center">Process the document to extract structured fields.</p>
      </div>
    );
  }

  const fields = data.fields;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
        <span className="text-sm text-gray-400">{fields.length} fields</span>
        <div className="flex items-center gap-1">
          <ExportDropdown documentId={documentId} />
          <button
            onClick={() => setShowJson(!showJson)}
            className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
            aria-label={showJson ? "Table view" : "JSON view"}
          >
            {showJson ? <Table2 className="w-4 h-4" /> : <Code className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {showJson ? (
          <pre className="p-4 text-xs text-gray-300 font-mono whitespace-pre-wrap">
            {JSON.stringify(fields, null, 2)}
          </pre>
        ) : (
          <div className="divide-y divide-gray-800/50">
            {fields.map((field) => (
              <button
                key={field.id}
                onClick={() => selectField(selectedFieldId === field.id ? null : field.id)}
                className={`w-full text-left px-4 py-3 hover:bg-gray-800/50 transition-colors ${
                  selectedFieldId === field.id ? "bg-blue-500/10 border-l-2 border-blue-400" : ""
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">{field.field_key ?? "—"}</span>
                  <ConfidenceBadge confidence={field.confidence} />
                </div>
                <p className="text-sm text-gray-400 truncate">{field.field_value}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-gray-600">Page {field.page_number}</span>
                  {field.is_required && (
                    <span className="text-xs text-blue-400/60">Required</span>
                  )}
                  {field.is_missing && (
                    <span className="text-xs text-red-400/60">Missing</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ExportDropdown({ documentId }: { documentId: string }) {
  const [open, setOpen] = useState(false);

  const handleExport = async (format: "json" | "csv") => {
    setOpen(false);
    try {
      const token = useAuthStore.getState().accessToken;
      const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
      const resp = await fetch(
        `${BASE_URL}/api/v1/extractions/${documentId}/export?format=${format}`,
        { headers: token ? { Authorization: `Bearer ${token}` } : {} },
      );
      if (!resp.ok) throw new Error("Export failed");

      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${documentId}_extraction.${format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (e) {
      toast.error(`Export failed: ${(e as Error).message}`);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
        title="Export"
      >
        <Download className="w-4 h-4" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-full mt-1 z-50 bg-[#12121a] border border-[#2a2a3a] rounded-lg shadow-xl py-1 w-32">
            <button
              onClick={() => handleExport("json")}
              className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-white/5 transition-colors"
            >
              Export JSON
            </button>
            <button
              onClick={() => handleExport("csv")}
              className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-white/5 transition-colors"
            >
              Export CSV
            </button>
          </div>
        </>
      )}
    </div>
  );
}
