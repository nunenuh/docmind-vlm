import { useState } from "react";
import {
  Bot, Plus, Copy, Trash2, ChevronDown, ChevronUp,
  Loader2, Search,
} from "lucide-react";
import { usePersonas, useDeletePersona, useDuplicatePersona } from "@/hooks/usePersonas";
import { PersonaSlideOver, type PanelMode } from "@/components/persona/PersonaSlideOver";
import type { PersonaResponse } from "@/types/api";

export function PersonasPage() {
  const { data, isLoading } = usePersonas();
  const deletePersona = useDeletePersona();
  const duplicatePersona = useDuplicatePersona();
  const [search, setSearch] = useState("");
  const [panelMode, setPanelMode] = useState<PanelMode | "closed">("closed");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const openDetail = (id: string) => { setSelectedId(id); setPanelMode("detail"); };
  const openCreate = () => { setSelectedId(null); setPanelMode("create"); };
  const closePanel = () => { setSelectedId(null); setPanelMode("closed"); };

  const personas: PersonaResponse[] = data ?? [];

  const filtered = personas.filter((p) =>
    !search || p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.description?.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="h-full bg-[#0B0D11] overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-gray-100">Personas</h1>
            <p className="text-[13px] text-gray-500 mt-1">
              AI personas define how the assistant behaves in project chats.
            </p>
          </div>
          <button
            onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 text-[13px] font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Persona
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-600" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search personas..."
            className="w-full pl-10 pr-4 py-2.5 text-[13px] bg-[#111318] border border-white/[0.06] rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/30 transition-colors"
          />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-8">
          <StatCard label="Total Personas" value={personas.length} />
          <StatCard label="With Rules" value={personas.filter((p) => p.rules).length} />
          <StatCard label="With Boundaries" value={personas.filter((p) => p.boundaries).length} />
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-14 h-14 rounded-2xl bg-gray-800/50 border border-gray-700/50 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-gray-600" />
            </div>
            <p className="text-[14px] text-gray-300 font-medium">
              {search ? "No matching personas" : "No personas yet"}
            </p>
            <p className="text-[12px] text-gray-600 mt-1">
              {search ? "Try a different search term." : "Create your first AI persona to customize chat behavior."}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {filtered.map((persona) => (
              <PersonaCard
                key={persona.id}
                persona={persona}
                onClick={() => openDetail(persona.id)}
                onDuplicate={() => duplicatePersona.mutate(persona.id)}
                onDelete={() => {
                  if (window.confirm(`Delete "${persona.name}"?`))
                    deletePersona.mutate(persona.id);
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Slide-over */}
      {panelMode !== "closed" && (
        <PersonaSlideOver
          personaId={selectedId}
          mode={panelMode}
          onClose={closePanel}
          onSwitchToEdit={() => setPanelMode("edit")}
          onOpenPersona={(id) => { setSelectedId(id); setPanelMode("detail"); }}
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

function PersonaCard({
  persona, onClick, onDuplicate, onDelete,
}: {
  persona: PersonaResponse;
  onClick: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      onClick={onClick}
      className="group p-4 bg-[#111318] border border-white/[0.05] rounded-xl hover:border-white/[0.1] transition-all cursor-pointer"
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-[13px] font-semibold text-gray-100">{persona.name}</h3>
          {persona.description && (
            <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-2 leading-relaxed">
              {persona.description}
            </p>
          )}
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={(e) => { e.stopPropagation(); onDuplicate(); }}
            className="p-1 text-gray-600 hover:text-indigo-400 rounded transition-colors"
          >
            <Copy className="w-3 h-3" />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            className="p-1 text-gray-600 hover:text-rose-400 rounded transition-colors"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Metadata pills */}
      <div className="flex items-center gap-2 mt-3 text-[10px]">
        <span className="px-2 py-0.5 bg-violet-500/10 text-violet-400 rounded capitalize">
          {persona.tone}
        </span>
        {persona.rules && (
          <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">
            Has rules
          </span>
        )}
        {persona.boundaries && (
          <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded">
            Has boundaries
          </span>
        )}
      </div>

      {/* Expandable prompt preview */}
      {persona.system_prompt && (
        <>
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="flex items-center gap-1 mt-3 text-[10px] text-gray-600 hover:text-gray-400 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            System prompt
          </button>
          {expanded && (
            <pre
              onClick={(e) => e.stopPropagation()}
              className="mt-2 text-[11px] text-gray-500 bg-[#0B0D11] border border-white/[0.05] rounded-lg p-3 max-h-24 overflow-y-auto whitespace-pre-wrap font-mono"
            >
              {persona.system_prompt}
            </pre>
          )}
        </>
      )}
    </div>
  );
}
