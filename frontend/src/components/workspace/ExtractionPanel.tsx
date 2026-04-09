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
  const isSummaryMode = fields.some((f) => f.field_type === "summary" || f.field_type === "section" || f.field_type === "entity");

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
        ) : isSummaryMode ? (
          <SummaryView fields={fields} />
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

/* ── Summary View for unstructured documents ────────── */

const ENTITY_COLORS: Record<string, string> = {
  person: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  org: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  date: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  email: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  phone: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
  address: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  skill: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  education: "bg-teal-500/10 text-teal-400 border-teal-500/20",
  job_title: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  other: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

interface FieldData {
  field_type: string;
  field_key: string | null;
  field_value: string;
  page_number: number;
  confidence: number;
}

function SummaryView({ fields }: { fields: FieldData[] }) {
  const summaryFields = fields.filter((f) => f.field_type === "summary");
  const sectionFields = fields.filter((f) => f.field_type === "section");
  const entityFields = fields.filter((f) => f.field_type === "entity");

  const docType = summaryFields.find((f) => f.field_key === "document_type")?.field_value;
  const summary = summaryFields.find((f) => f.field_key === "summary")?.field_value;
  const language = summaryFields.find((f) => f.field_key === "language")?.field_value;

  // Group entities by type
  const entityGroups: Record<string, FieldData[]> = {};
  for (const e of entityFields) {
    const key = e.field_key || "other";
    if (!entityGroups[key]) entityGroups[key] = [];
    entityGroups[key].push(e);
  }

  return (
    <div className="px-4 py-3 space-y-4">
      {/* Document type + language */}
      <div className="flex items-center gap-2 flex-wrap">
        {docType && (
          <span className="px-2.5 py-1 text-[11px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded capitalize">
            {docType}
          </span>
        )}
        {language && (
          <span className="px-2.5 py-1 text-[11px] font-medium bg-gray-500/10 text-gray-400 border border-gray-500/20 rounded">
            {language}
          </span>
        )}
      </div>

      {/* Summary */}
      {summary && (
        <div>
          <h4 className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1.5">Summary</h4>
          <p className="text-[13px] text-gray-300 leading-relaxed">{summary}</p>
        </div>
      )}

      {/* Sections */}
      {sectionFields.length > 0 && (
        <div>
          <h4 className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-2">
            Sections ({sectionFields.length})
          </h4>
          <div className="space-y-1.5">
            {sectionFields.map((s, i) => (
              <div key={i} className="px-3 py-2 bg-gray-800/30 border border-gray-800/50 rounded-lg">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[12px] font-medium text-gray-200">{s.field_key}</span>
                  <span className="text-[10px] text-gray-600">p.{s.page_number}</span>
                </div>
                {s.field_value && (
                  <p className="text-[11px] text-gray-500 line-clamp-2">{s.field_value}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Entities */}
      {entityFields.length > 0 && (
        <div>
          <h4 className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-2">
            Entities ({entityFields.length})
          </h4>
          <div className="space-y-2">
            {Object.entries(entityGroups).map(([type, entities]) => (
              <div key={type}>
                <span className="text-[10px] text-gray-600 capitalize mb-1 block">{type}</span>
                <div className="flex flex-wrap gap-1">
                  {entities.map((e, i) => (
                    <span
                      key={i}
                      className={`px-2 py-0.5 text-[11px] rounded border ${ENTITY_COLORS[type] || ENTITY_COLORS.other}`}
                    >
                      {e.field_value}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
