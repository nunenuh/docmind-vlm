import { useState, useEffect } from "react";
import { X, Loader2 } from "lucide-react";
import { useCreatePersona, useUpdatePersona } from "@/hooks/usePersonas";
import type { PersonaResponse } from "@/types/api";

const TONE_OPTIONS = ["professional", "friendly", "formal", "casual", "technical"];

interface PersonaEditorProps {
  persona?: PersonaResponse | null;
  onClose: () => void;
  onSaved?: (persona: PersonaResponse) => void;
}

export function PersonaEditor({ persona, onClose, onSaved }: PersonaEditorProps) {
  const createPersona = useCreatePersona();
  const updatePersona = useUpdatePersona();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [tone, setTone] = useState("professional");
  const [rules, setRules] = useState("");
  const [boundaries, setBoundaries] = useState("");

  useEffect(() => {
    if (persona) {
      setName(persona.name);
      setDescription(persona.description ?? "");
      setSystemPrompt(persona.system_prompt);
      setTone(persona.tone);
      setRules(persona.rules ?? "");
      setBoundaries(persona.boundaries ?? "");
    }
  }, [persona]);

  const isEditing = !!persona;
  const isPending = createPersona.isPending || updatePersona.isPending;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !systemPrompt.trim()) return;

    const data = {
      name: name.trim(),
      description: description.trim() || undefined,
      system_prompt: systemPrompt.trim(),
      tone,
      rules: rules.trim() || undefined,
      boundaries: boundaries.trim() || undefined,
    };

    if (isEditing && persona) {
      updatePersona.mutate(
        { id: persona.id, data },
        {
          onSuccess: (result) => {
            onSaved?.(result);
            onClose();
          },
        },
      );
    } else {
      createPersona.mutate(data, {
        onSuccess: (result) => {
          onSaved?.(result);
          onClose();
        },
      });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-800 rounded-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-white">
            {isEditing ? "Edit Persona" : "Create Persona"}
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Legal Analyst"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of this persona"
              rows={2}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">System Prompt *</label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="You are a helpful assistant that..."
              rows={5}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
              required
            />
          </div>

          {/* Tone */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Tone</label>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
            >
              {TONE_OPTIONS.map((t) => (
                <option key={t} value={t}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Rules */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Rules</label>
            <textarea
              value={rules}
              onChange={(e) => setRules(e.target.value)}
              placeholder="Always cite sources. Never give medical advice."
              rows={3}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {/* Boundaries */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Boundaries</label>
            <textarea
              value={boundaries}
              onChange={(e) => setBoundaries(e.target.value)}
              placeholder="Do not discuss topics outside the uploaded documents."
              rows={3}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || !name.trim() || !systemPrompt.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
            >
              {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {isEditing ? "Save Changes" : "Create Persona"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
