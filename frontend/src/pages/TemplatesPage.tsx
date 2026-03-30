import { useState } from "react";
import {
  LayoutTemplate, Plus, Copy, Trash2, ChevronRight,
  FileText, Loader2, Lock, Search,
} from "lucide-react";
import { useTemplates, useDeleteTemplate, useDuplicateTemplate } from "@/hooks/useTemplates";
import { TemplateSlideOver, type PanelMode } from "@/components/template/TemplateSlideOver";
import type { TemplateSummary } from "@/types/api";

const CATEGORY_LABELS: Record<string, string> = {
  government: "Government",
  finance: "Finance",
  identity: "Identity",
  general: "General",
  custom: "Custom",
};

const CATEGORY_COLORS: Record<string, string> = {
  government: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  finance: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  identity: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  general: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  custom: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

export function TemplatesPage() {
  const { data, isLoading } = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const duplicateTemplate = useDuplicateTemplate();
  const [search, setSearch] = useState("");
  const [panelMode, setPanelMode] = useState<PanelMode | "closed">("closed");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const openDetail = (id: string) => { setSelectedId(id); setPanelMode("detail"); };
  const openCreate = () => { setSelectedId(null); setPanelMode("create"); };
  const closePanel = () => { setSelectedId(null); setPanelMode("closed"); };

  const templates: TemplateSummary[] = data?.items ?? [];

  const filtered = templates.filter((t) =>
    !search || t.name.toLowerCase().includes(search.toLowerCase()) ||
    t.type.toLowerCase().includes(search.toLowerCase())
  );

  // Group by category
  const grouped = filtered.reduce<Record<string, TemplateSummary[]>>((acc, t) => {
    const cat = t.category || "general";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(t);
    return acc;
  }, {});

  const categories = Object.keys(grouped).sort((a, b) => {
    if (a === "custom") return 1;
    if (b === "custom") return -1;
    return a.localeCompare(b);
  });

  return (
    <div className="h-full bg-[#0B0D11] overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-100">Templates</h1>
            <p className="text-[13px] text-gray-500 mt-1">
              Extraction templates define which fields to extract from each document type.
            </p>
          </div>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Template
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search templates..."
            className="w-full pl-10 pr-4 py-2.5 text-[13px] bg-[#111318] border border-white/[0.06] rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/30 transition-colors"
          />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-8">
          <StatCard label="Templates" value={templates.length} />
          <StatCard label="Categories" value={categories.length} />
          <StatCard label="Total Fields" value={templates.reduce((sum, t) => sum + t.total_field_count, 0)} />
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
          </div>
        ) : templates.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gray-800/50 border border-gray-700/50 flex items-center justify-center mb-4">
              <LayoutTemplate className="w-6 h-6 text-gray-600" />
            </div>
            <p className="text-[14px] text-gray-300 font-medium">No templates yet</p>
            <p className="text-[12px] text-gray-600 mt-1">Create your first extraction template to get started.</p>
          </div>
        ) : (
          <div className="space-y-8">
            {categories.map((cat) => (
              <div key={cat}>
                <div className="flex items-center gap-2 mb-3">
                  <span className={`text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded border ${
                    CATEGORY_COLORS[cat] || CATEGORY_COLORS.general
                  }`}>
                    {CATEGORY_LABELS[cat] || cat}
                  </span>
                  <span className="text-[11px] text-gray-600">{grouped[cat].length}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {grouped[cat].map((template) => (
                    <TemplateCard
                      key={template.id}
                      template={template}
                      onClick={() => openDetail(template.id)}
                      onDuplicate={() => duplicateTemplate.mutate(template.id)}
                      onDelete={() => {
                        if (window.confirm(`Delete "${template.name}"?`))
                          deleteTemplate.mutate(template.id);
                      }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Slide-over */}
      {panelMode !== "closed" && (
        <TemplateSlideOver
          templateId={selectedId}
          mode={panelMode}
          onClose={closePanel}
          onSwitchToEdit={() => setPanelMode("edit")}
          onOpenTemplate={(id) => { setSelectedId(id); setPanelMode("detail"); }}
        />
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="px-4 py-3 bg-[#111318] border border-white/[0.05] rounded-lg">
      <p className="text-[11px] text-gray-500 uppercase tracking-wider">{label}</p>
      <p className="text-xl font-bold text-gray-100 mt-1">{value}</p>
    </div>
  );
}

function TemplateCard({
  template, onClick, onDuplicate, onDelete,
}: {
  template: TemplateSummary;
  onClick: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  return (
    <div onClick={onClick} className="group p-4 bg-[#111318] border border-white/[0.05] rounded-xl hover:border-white/[0.1] transition-all cursor-pointer">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center">
            <FileText className="w-4 h-4 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-[13px] font-semibold text-gray-100">{template.name}</h3>
            <p className="text-[10px] text-gray-600 font-mono">{template.type}</p>
          </div>
        </div>
      </div>

      {template.description && (
        <p className="text-[11px] text-gray-500 line-clamp-2 mb-3 leading-relaxed">
          {template.description}
        </p>
      )}

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[10px] text-gray-600">
          <span>{template.total_field_count} fields</span>
          <span>{template.required_field_count} required</span>
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => { e.stopPropagation(); onDuplicate(); }}
            className="p-1 text-gray-600 hover:text-indigo-400 rounded transition-colors"
            title="Duplicate"
          >
            <Copy className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="p-1 text-gray-600 hover:text-rose-400 rounded transition-colors"
            title="Delete"
          >
            <Trash2 className="w-3 h-3" />
          </button>
          <ChevronRight className="w-3 h-3 text-gray-600" />
        </div>
      </div>
    </div>
  );
}
