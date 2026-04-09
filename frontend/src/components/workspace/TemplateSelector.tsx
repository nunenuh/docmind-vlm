import { useState } from "react";
import { FileText, ChevronDown, Check, Sparkles, Tag } from "lucide-react";
import { useTemplates } from "@/hooks/useTemplates";
import type { TemplateSummary } from "@/types/api";

interface TemplateSelectorProps {
  value: string | null;
  onChange: (templateId: string | null, templateType: string | null) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  identity: "text-blue-400 bg-blue-400/10",
  vehicle: "text-emerald-400 bg-emerald-400/10",
  tax: "text-amber-400 bg-amber-400/10",
  finance: "text-violet-400 bg-violet-400/10",
  legal: "text-rose-400 bg-rose-400/10",
  general: "text-gray-400 bg-gray-400/10",
  custom: "text-indigo-400 bg-indigo-400/10",
};

export function TemplateSelector({ value, onChange }: TemplateSelectorProps) {
  const [open, setOpen] = useState(false);
  const { data } = useTemplates();
  const templates = data?.items ?? [];

  const selected = templates.find((t) => t.id === value);

  // Group by category
  const grouped = templates.reduce<Record<string, TemplateSummary[]>>((acc, t) => {
    const cat = t.category || "general";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(t);
    return acc;
  }, {});

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2.5 bg-[#0a0a0f] border border-[#2a2a3a] rounded-xl text-left text-sm hover:border-[#3a3a4a] transition-colors"
      >
        {selected ? (
          <>
            <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${CATEGORY_COLORS[selected.category] || CATEGORY_COLORS.general}`}>
              {selected.category}
            </span>
            <span className="text-white truncate flex-1">{selected.name}</span>
            <span className="text-xs text-gray-500">{selected.total_field_count} fields</span>
          </>
        ) : (
          <>
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <span className="text-gray-400 flex-1">Auto-detect (recommended)</span>
          </>
        )}
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute top-full left-0 right-0 mt-1 z-50 bg-[#12121a] border border-[#2a2a3a] rounded-xl shadow-2xl max-h-80 overflow-y-auto">
            {/* Auto-detect option */}
            <button
              onClick={() => { onChange(null, null); setOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm hover:bg-white/5 transition-colors ${
                !value ? "text-white bg-indigo-500/10" : "text-gray-300"
              }`}
            >
              <Sparkles className="w-4 h-4 text-indigo-400" />
              <div className="flex-1 text-left">
                <div className="font-medium">Auto-detect</div>
                <div className="text-xs text-gray-500">AI identifies document type automatically</div>
              </div>
              {!value && <Check className="w-4 h-4 text-indigo-400" />}
            </button>

            <div className="border-t border-[#1e1e2e] my-1" />

            {/* Grouped templates */}
            {Object.entries(grouped).map(([category, items]) => (
              <div key={category}>
                <div className="px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-gray-600">
                  {category}
                </div>
                {items.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => { onChange(t.id, t.type); setOpen(false); }}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-sm hover:bg-white/5 transition-colors ${
                      value === t.id ? "text-white bg-indigo-500/10" : "text-gray-300"
                    }`}
                  >
                    <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    <div className="flex-1 text-left min-w-0">
                      <div className="truncate">{t.name}</div>
                      {t.description && (
                        <div className="text-xs text-gray-500 truncate">{t.description}</div>
                      )}
                    </div>
                    <span className="text-xs text-gray-600 flex-shrink-0">{t.total_field_count}f</span>
                    {t.is_preset && <Tag className="w-3 h-3 text-gray-600" />}
                    {value === t.id && <Check className="w-4 h-4 text-indigo-400 flex-shrink-0" />}
                  </button>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
