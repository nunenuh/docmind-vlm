import { Loader2, Pencil, Copy, Trash2, Bot } from "lucide-react";
import { usePersonaDetail, useDeletePersona, useDuplicatePersona } from "@/hooks/usePersonas";

interface Props {
  personaId: string;
  onEdit: () => void;
  onClose: () => void;
  onDuplicated: (newId: string) => void;
}

export function PersonaDetailView({ personaId, onEdit, onClose, onDuplicated }: Props) {
  const { data: persona, isLoading } = usePersonaDetail(personaId);
  const deleteMutation = useDeletePersona();
  const duplicateMutation = useDuplicatePersona();

  if (isLoading || !persona) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const handleDuplicate = () => {
    duplicateMutation.mutate(personaId, {
      onSuccess: (data: unknown) => {
        const result = data as { id?: string } | undefined;
        if (result?.id) onDuplicated(result.id);
        else onClose();
      },
    });
  };

  const handleDelete = () => {
    if (!window.confirm(`Delete "${persona.name}"? This cannot be undone.`)) return;
    deleteMutation.mutate(personaId, { onSuccess: onClose });
  };

  const parseList = (val: string | null | undefined): string[] => {
    if (!val) return [];
    try {
      const parsed = JSON.parse(val);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return val ? [val] : [];
    }
  };

  const rules = parseList(persona.rules);
  const boundaries = parseList(persona.boundaries);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
            <Bot className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-[15px] font-bold text-gray-100">{persona.name}</h3>
            {persona.description && (
              <p className="text-[12px] text-gray-400 mt-1 leading-relaxed">{persona.description}</p>
            )}
          </div>
        </div>

        {/* Tone */}
        <div className="flex items-center gap-3 text-[11px]">
          <span className="text-gray-500">Tone:</span>
          <span className="px-2 py-0.5 bg-violet-500/10 text-violet-400 rounded capitalize">{persona.tone}</span>
        </div>

        {/* System Prompt */}
        <div>
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider block mb-1.5">
            System Prompt
          </span>
          <div className="px-3 py-2.5 bg-[#0B0D11] border border-white/[0.05] rounded-lg text-[11px] font-mono text-gray-400 leading-relaxed max-h-[200px] overflow-y-auto whitespace-pre-wrap">
            {persona.system_prompt || "—"}
          </div>
        </div>

        {/* Rules */}
        {rules.length > 0 && (
          <div>
            <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider block mb-1.5">
              Rules ({rules.length})
            </span>
            <ul className="space-y-1">
              {rules.map((rule, i) => (
                <li key={i} className="flex items-start gap-2 text-[11px] text-gray-400">
                  <span className="text-emerald-400 mt-0.5 flex-shrink-0">•</span>
                  {rule}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Boundaries */}
        {boundaries.length > 0 && (
          <div>
            <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider block mb-1.5">
              Boundaries ({boundaries.length})
            </span>
            <ul className="space-y-1">
              {boundaries.map((b, i) => (
                <li key={i} className="flex items-start gap-2 text-[11px] text-gray-400">
                  <span className="text-amber-400 mt-0.5 flex-shrink-0">•</span>
                  {b}
                </li>
              ))}
            </ul>
          </div>
        )}
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
          <Copy className="w-3.5 h-3.5" />
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
