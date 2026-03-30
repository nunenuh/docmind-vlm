import { useEffect } from "react";
import { X } from "lucide-react";
import { PersonaDetailView } from "./PersonaDetailView";
import { PersonaForm } from "./PersonaForm";

export type PanelMode = "detail" | "create" | "edit";

interface Props {
  personaId: string | null;
  mode: PanelMode;
  onClose: () => void;
  onSwitchToEdit: () => void;
  onOpenPersona: (id: string) => void;
}

export function PersonaSlideOver({ personaId, mode, onClose, onSwitchToEdit, onOpenPersona }: Props) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const title =
    mode === "create" ? "New Persona" :
    mode === "edit" ? "Edit Persona" :
    "Persona Detail";

  return (
    <>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-xl bg-[#111318] border-l border-white/[0.06] z-50 shadow-2xl shadow-black/50 flex flex-col">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/[0.05] flex-shrink-0">
          <h2 className="text-[14px] font-semibold text-gray-100">{title}</h2>
          <button onClick={onClose} className="p-1.5 text-gray-500 hover:text-white rounded-lg hover:bg-white/[0.06] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {mode === "detail" && personaId && (
          <PersonaDetailView
            personaId={personaId}
            onEdit={onSwitchToEdit}
            onClose={onClose}
            onDuplicated={onOpenPersona}
          />
        )}
        {mode === "create" && <PersonaForm onClose={onClose} />}
        {mode === "edit" && personaId && <PersonaForm personaId={personaId} onClose={onClose} />}
      </div>
    </>
  );
}
