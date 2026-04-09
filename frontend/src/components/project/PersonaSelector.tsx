import { useState } from "react";
import { Bot, ChevronDown, Plus, X } from "lucide-react";
import { usePersonas } from "@/hooks/usePersonas";
import type { PersonaResponse } from "@/types/api";

interface PersonaSelectorProps {
  value: string | null;
  onChange: (personaId: string | null) => void;
  onCreateNew?: () => void;
}

export function PersonaSelector({ value, onChange, onCreateNew }: PersonaSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { data: personas } = usePersonas();

  const selected = personas?.find((p: PersonaResponse) => p.id === value);
  const presets = personas?.filter((p: PersonaResponse) => p.is_preset) ?? [];
  const custom = personas?.filter((p: PersonaResponse) => !p.is_preset) ?? [];

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between gap-2 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-left hover:border-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Bot className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <span className={selected ? "text-white" : "text-gray-500"}>
            {selected ? selected.name : "No persona"}
          </span>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />

          {/* Dropdown */}
          <div className="absolute z-20 mt-1 w-full bg-gray-900 border border-gray-700 rounded-lg shadow-xl max-h-60 overflow-y-auto">
            {/* No persona option */}
            <button
              type="button"
              onClick={() => { onChange(null); setIsOpen(false); }}
              className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-800 transition-colors ${
                !value ? "text-blue-400" : "text-gray-400"
              }`}
            >
              <div className="flex items-center gap-2">
                <X className="w-3.5 h-3.5" />
                No persona
              </div>
            </button>

            {/* Preset personas */}
            {presets.length > 0 && (
              <>
                <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-600 uppercase tracking-wider">
                  Presets
                </div>
                {presets.map((p: PersonaResponse) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => { onChange(p.id); setIsOpen(false); }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-800 transition-colors ${
                      value === p.id ? "text-blue-400" : "text-white"
                    }`}
                  >
                    <div className="font-medium">{p.name}</div>
                    {p.description && (
                      <div className="text-xs text-gray-500 truncate mt-0.5">{p.description}</div>
                    )}
                  </button>
                ))}
              </>
            )}

            {/* Custom personas */}
            {custom.length > 0 && (
              <>
                <div className="px-3 py-1.5 text-[10px] font-semibold text-gray-600 uppercase tracking-wider">
                  Custom
                </div>
                {custom.map((p: PersonaResponse) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => { onChange(p.id); setIsOpen(false); }}
                    className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-800 transition-colors ${
                      value === p.id ? "text-blue-400" : "text-white"
                    }`}
                  >
                    <div className="font-medium">{p.name}</div>
                    {p.description && (
                      <div className="text-xs text-gray-500 truncate mt-0.5">{p.description}</div>
                    )}
                  </button>
                ))}
              </>
            )}

            {/* Create new */}
            {onCreateNew && (
              <button
                type="button"
                onClick={() => { onCreateNew(); setIsOpen(false); }}
                className="w-full text-left px-3 py-2 text-sm text-blue-400 hover:bg-gray-800 transition-colors border-t border-gray-800"
              >
                <div className="flex items-center gap-2">
                  <Plus className="w-3.5 h-3.5" />
                  Create Custom...
                </div>
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
