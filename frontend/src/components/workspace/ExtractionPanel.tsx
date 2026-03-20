import { useState } from "react";
import { Code, Table2, Loader2, FileSearch } from "lucide-react";
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
        <span className="text-sm text-gray-400">{fields.length} fields extracted</span>
        <button
          onClick={() => setShowJson(!showJson)}
          className="p-1.5 rounded hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          aria-label={showJson ? "Table view" : "JSON view"}
        >
          {showJson ? <Table2 className="w-4 h-4" /> : <Code className="w-4 h-4" />}
        </button>
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
