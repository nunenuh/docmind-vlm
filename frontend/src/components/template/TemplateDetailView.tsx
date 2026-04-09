import { Loader2, Lock, Copy, Pencil, Trash2, FileText } from "lucide-react";
import { useTemplateDetail, useDeleteTemplate, useDuplicateTemplate } from "@/hooks/useTemplates";
import type { TemplateFieldDef } from "@/types/api";

const TYPE_BADGES: Record<string, string> = {
  string: "bg-gray-500/10 text-gray-400",
  date: "bg-blue-500/10 text-blue-400",
  enum: "bg-violet-500/10 text-violet-400",
  table: "bg-amber-500/10 text-amber-400",
  number: "bg-emerald-500/10 text-emerald-400",
  boolean: "bg-rose-500/10 text-rose-400",
};

interface Props {
  templateId: string;
  onEdit: () => void;
  onClose: () => void;
  onDuplicated: (newId: string) => void;
}

export function TemplateDetailView({ templateId, onEdit, onClose, onDuplicated }: Props) {
  const { data: template, isLoading } = useTemplateDetail(templateId);
  const deleteMutation = useDeleteTemplate();
  const duplicateMutation = useDuplicateTemplate();

  if (isLoading || !template) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const handleDuplicate = () => {
    duplicateMutation.mutate(templateId, {
      onSuccess: (data: unknown) => {
        const result = data as { id?: string } | undefined;
        if (result?.id) onDuplicated(result.id);
        else onClose();
      },
    });
  };

  const handleDelete = () => {
    if (!window.confirm(`Delete "${template.name}"? This cannot be undone.`)) return;
    deleteMutation.mutate(templateId, { onSuccess: onClose });
  };

  const fields: TemplateFieldDef[] = template.fields || [];
  const requiredCount = fields.filter((f) => f.required).length;

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        {/* Header info */}
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-[15px] font-bold text-gray-100">{template.name}</h3>
          </div>
          <p className="text-[11px] font-mono text-gray-500">{template.type}</p>
          {template.description && (
            <p className="text-[12px] text-gray-400 mt-2 leading-relaxed">{template.description}</p>
          )}
        </div>

        {/* Category */}
        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-gray-500">Category:</span>
          <span className="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded capitalize">{template.category}</span>
        </div>

        {/* Extraction prompt */}
        {template.extraction_prompt && (
          <div>
            <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider block mb-1.5">
              Extraction Prompt
            </span>
            <div className="px-3 py-2.5 bg-[#0B0D11] border border-white/[0.05] rounded-lg text-[11px] font-mono text-gray-400 leading-relaxed max-h-[120px] overflow-y-auto">
              {template.extraction_prompt}
            </div>
          </div>
        )}

        {/* Fields table */}
        <div>
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider block mb-2">
            Fields ({fields.length} total, {requiredCount} required)
          </span>

          {fields.length === 0 ? (
            <p className="text-[11px] text-gray-600 py-4 text-center">No fields defined</p>
          ) : (
            <div className="border border-white/[0.05] rounded-lg overflow-hidden">
              {/* Table header */}
              <div className="flex items-center gap-3 px-3 py-2 bg-white/[0.02] text-[9px] text-gray-600 uppercase tracking-wider border-b border-white/[0.05]">
                <span className="w-[90px]">Key</span>
                <span className="flex-1">Label</span>
                <span className="w-[60px]">Type</span>
                <span className="w-[36px] text-center">Req</span>
              </div>
              {/* Rows */}
              {fields.map((f, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-3 px-3 py-2 text-[11px] ${
                    i < fields.length - 1 ? "border-b border-white/[0.03]" : ""
                  }`}
                >
                  <span className="w-[90px] font-mono text-gray-300 truncate">{f.key}</span>
                  <span className="flex-1 text-gray-400 truncate">{f.label}</span>
                  <span className={`w-[60px] px-1.5 py-0.5 text-[9px] font-medium rounded text-center ${
                    TYPE_BADGES[f.type] || TYPE_BADGES.string
                  }`}>
                    {f.type}
                  </span>
                  <span className="w-[36px] text-center">
                    {f.required ? (
                      <span className="text-indigo-400 text-[10px]">Yes</span>
                    ) : (
                      <span className="text-gray-700 text-[10px]">—</span>
                    )}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Action bar */}
      <div className="flex items-center gap-2 px-5 py-3 border-t border-white/[0.05] flex-shrink-0">
        <button
          onClick={onEdit}
          className="flex items-center gap-2 px-4 py-2 text-[12px] font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
        >
          <Pencil className="w-3.5 h-3.5" />
          Edit
        </button>
        <button
          onClick={handleDuplicate}
          disabled={duplicateMutation.isPending}
          className="flex items-center gap-2 px-3 py-2 text-[12px] font-medium text-gray-400 hover:text-gray-200 rounded-lg hover:bg-white/[0.04] transition-colors"
        >
          {duplicateMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Copy className="w-3.5 h-3.5" />}
          Duplicate
        </button>
        <div className="flex-1" />
        <button
          onClick={handleDelete}
          disabled={deleteMutation.isPending}
          className="flex items-center gap-2 px-3 py-2 text-[12px] font-medium text-rose-400/70 hover:text-rose-400 rounded-lg hover:bg-rose-500/[0.06] transition-colors"
        >
          <Trash2 className="w-3.5 h-3.5" />
          Delete
        </button>
      </div>
    </div>
  );
}
