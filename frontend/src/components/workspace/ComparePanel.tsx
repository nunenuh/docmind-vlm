import { Loader2, ArrowRight } from "lucide-react";
import { useComparison } from "@/hooks/useExtraction";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface ComparePanelProps {
  documentId: string;
}

export function ComparePanel({ documentId }: ComparePanelProps) {
  const { data, isLoading } = useComparison(documentId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No comparison data available.</p>
      </div>
    );
  }

  const { enhanced_fields, corrected, added } = data;
  const correctedSet = new Set(corrected);
  const addedSet = new Set(added);

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2 border-b border-gray-800 flex items-center gap-4">
        <span className="text-xs text-gray-400">{enhanced_fields.length} fields</span>
        {corrected.length > 0 && (
          <span className="text-xs text-yellow-400">{corrected.length} corrected</span>
        )}
        {added.length > 0 && (
          <span className="text-xs text-green-400">{added.length} added</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto divide-y divide-gray-800/50">
        {enhanced_fields.map((field) => {
          const isCorrected = correctedSet.has(field.id);
          const isAdded = addedSet.has(field.id);

          let borderClass = "";
          if (isCorrected) borderClass = "border-l-2 border-yellow-400 bg-yellow-500/5";
          else if (isAdded) borderClass = "border-l-2 border-green-400 bg-green-500/5";

          return (
            <div key={field.id} className={`px-4 py-3 ${borderClass}`}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-white">{field.field_key ?? "—"}</span>
                  {isCorrected && <span className="text-xs text-yellow-400">corrected</span>}
                  {isAdded && <span className="text-xs text-green-400">added</span>}
                </div>
                <ConfidenceBadge confidence={field.confidence} />
              </div>
              <p className="text-sm text-gray-400">{field.field_value}</p>
              <div className="flex items-center gap-3 mt-1 text-xs text-gray-600">
                <span>VLM: {Math.round(field.vlm_confidence * 100)}%</span>
                <ArrowRight className="w-3 h-3" />
                <span>Final: {Math.round(field.confidence * 100)}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
