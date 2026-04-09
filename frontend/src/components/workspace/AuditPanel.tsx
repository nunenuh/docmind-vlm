import { Clock, Loader2, CheckCircle } from "lucide-react";
import { useAuditTrail } from "@/hooks/useExtraction";

interface AuditPanelProps {
  documentId: string;
}

export function AuditPanel({ documentId }: AuditPanelProps) {
  const { data: entries, isLoading } = useAuditTrail(documentId);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
        <p className="text-xs text-gray-500 mt-3">Loading audit trail...</p>
      </div>
    );
  }

  if (!entries || entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-6">
        <div className="w-12 h-12 rounded-xl bg-gray-900 border border-gray-800 flex items-center justify-center mb-4">
          <Clock className="w-6 h-6 text-gray-700" />
        </div>
        <p className="text-sm font-medium text-gray-400 mb-1">No audit trail</p>
        <p className="text-xs text-gray-600 text-center">Processing history will appear here after the document is processed.</p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <h3 className="text-sm font-medium text-gray-400 mb-4">Processing Timeline</h3>
      {entries.map((entry, i) => (
        <div key={i} className="flex items-start gap-3">
          <div className="mt-0.5">
            <CheckCircle className="w-4 h-4 text-green-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white capitalize">
                {entry.step_name}
              </span>
              <span className="text-xs text-gray-500">
                {entry.duration_ms}ms
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Step {entry.step_order}
            </p>
          </div>
        </div>
      ))}
      <div className="pt-2 border-t border-gray-800">
        <p className="text-xs text-gray-600">
          Total: {entries.reduce((sum, e) => sum + e.duration_ms, 0)}ms
        </p>
      </div>
    </div>
  );
}
