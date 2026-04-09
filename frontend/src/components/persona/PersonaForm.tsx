import { useState, useEffect } from "react";
import { Loader2, Plus, X } from "lucide-react";
import { usePersonaDetail, useCreatePersona, useUpdatePersona } from "@/hooks/usePersonas";

interface Props {
  personaId?: string;
  onClose: () => void;
  onSaved?: () => void;
}

export function PersonaForm({ personaId, onClose, onSaved }: Props) {
  const isEdit = !!personaId;
  const { data: existing, isLoading } = usePersonaDetail(personaId ?? "");
  const createMutation = useCreatePersona();
  const updateMutation = useUpdatePersona();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [tone, setTone] = useState("professional");
  const [rules, setRules] = useState<string[]>([]);
  const [boundaries, setBoundaries] = useState<string[]>([]);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    if (isEdit && existing && !initialized) {
      setName(existing.name);
      setDescription(existing.description || "");
      setSystemPrompt(existing.system_prompt || "");
      setTone(existing.tone || "professional");

      const parseList = (val: string | null | undefined): string[] => {
        if (!val) return [];
        try { const p = JSON.parse(val); return Array.isArray(p) ? p : []; }
        catch { return val ? [val] : []; }
      };

      setRules(parseList(existing.rules));
      setBoundaries(parseList(existing.boundaries));
      setInitialized(true);
    }
  }, [isEdit, existing, initialized]);

  const handleSubmit = () => {
    const payload = {
      name: name.trim(),
      description: description || undefined,
      system_prompt: systemPrompt,
      tone,
      rules: JSON.stringify(rules.filter(Boolean)),
      boundaries: JSON.stringify(boundaries.filter(Boolean)),
    };

    if (isEdit && personaId) {
      updateMutation.mutate({ id: personaId, data: payload }, {
        onSuccess: () => { onSaved?.(); onClose(); },
      });
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => { onSaved?.(); onClose(); },
      });
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const canSubmit = name.trim() && !isPending;

  if (isEdit && isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const inputCls = "w-full px-3 py-2 text-[12px] bg-[#0B0D11] border border-white/[0.06] rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/30 disabled:opacity-50 transition-colors";

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {/* Name */}
        <label className="block">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">
            Name <span className="text-rose-400">*</span>
          </span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., Customer Service Agent" className={inputCls} autoFocus />
        </label>

        {/* Description */}
        <label className="block">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">Description</span>
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Brief description" className={inputCls} />
        </label>

        {/* Tone */}
        <label className="block">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">Tone</span>
          <select value={tone} onChange={(e) => setTone(e.target.value)} className={inputCls}>
            <option value="friendly">Friendly</option>
            <option value="professional">Professional</option>
            <option value="formal">Formal</option>
            <option value="precise">Precise</option>
            <option value="simple">Simple</option>
            <option value="casual">Casual</option>
          </select>
        </label>

        {/* System Prompt */}
        <label className="block">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">System Prompt</span>
          <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} placeholder="You are a..." rows={6} className={`${inputCls} resize-none font-mono`} />
        </label>

        {/* Rules */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Rules ({rules.length})</span>
            <button
              onClick={() => setRules([...rules, ""])}
              className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium text-indigo-400 bg-indigo-500/[0.08] hover:bg-indigo-500/[0.12] rounded transition-colors"
            >
              <Plus className="w-2.5 h-2.5" />
              Add
            </button>
          </div>
          <div className="space-y-1.5">
            {rules.map((rule, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span className="text-emerald-400 text-[10px] flex-shrink-0 w-3">•</span>
                <input
                  value={rule}
                  onChange={(e) => setRules(rules.map((r, j) => j === i ? e.target.value : r))}
                  placeholder="Rule..."
                  className={`flex-1 ${inputCls}`}
                />
                <button onClick={() => setRules(rules.filter((_, j) => j !== i))} className="p-1 text-gray-600 hover:text-rose-400">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Boundaries */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Boundaries ({boundaries.length})</span>
            <button
              onClick={() => setBoundaries([...boundaries, ""])}
              className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium text-indigo-400 bg-indigo-500/[0.08] hover:bg-indigo-500/[0.12] rounded transition-colors"
            >
              <Plus className="w-2.5 h-2.5" />
              Add
            </button>
          </div>
          <div className="space-y-1.5">
            {boundaries.map((b, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span className="text-amber-400 text-[10px] flex-shrink-0 w-3">•</span>
                <input
                  value={b}
                  onChange={(e) => setBoundaries(boundaries.map((x, j) => j === i ? e.target.value : x))}
                  placeholder="Boundary..."
                  className={`flex-1 ${inputCls}`}
                />
                <button onClick={() => setBoundaries(boundaries.filter((_, j) => j !== i))} className="p-1 text-gray-600 hover:text-rose-400">
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-white/[0.05] flex-shrink-0">
        <button onClick={onClose} className="px-4 py-2 text-[12px] font-medium text-gray-400 hover:text-gray-200 rounded-lg hover:bg-white/[0.04]">
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="flex items-center gap-2 px-4 py-2 text-[12px] font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {isEdit ? "Save Changes" : "Create Persona"}
        </button>
      </div>
    </div>
  );
}
