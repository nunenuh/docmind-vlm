import { Plus } from "lucide-react";
import { FieldRow } from "./FieldRow";
import type { TemplateFieldDef } from "@/types/api";

interface Props {
  fields: TemplateFieldDef[];
  onChange: (fields: TemplateFieldDef[]) => void;
  disabled?: boolean;
}

export function TemplateFieldEditor({ fields, onChange, disabled }: Props) {
  const addField = () => {
    onChange([...fields, { key: "", label: "", type: "string", required: false }]);
  };

  const updateField = (index: number, patch: Partial<TemplateFieldDef>) => {
    onChange(fields.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  };

  const removeField = (index: number) => {
    onChange(fields.filter((_, i) => i !== index));
  };

  const moveUp = (index: number) => {
    if (index === 0) return;
    const next = [...fields];
    [next[index - 1], next[index]] = [next[index], next[index - 1]];
    onChange(next);
  };

  const moveDown = (index: number) => {
    if (index === fields.length - 1) return;
    const next = [...fields];
    [next[index], next[index + 1]] = [next[index + 1], next[index]];
    onChange(next);
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">
          Fields ({fields.length})
        </span>
        {!disabled && (
          <button
            onClick={addField}
            className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-indigo-400 bg-indigo-500/[0.08] hover:bg-indigo-500/[0.12] rounded transition-colors"
          >
            <Plus className="w-3 h-3" />
            Add Field
          </button>
        )}
      </div>

      {/* Column labels */}
      {fields.length > 0 && (
        <div className="flex items-center gap-1.5 px-0 pb-1 text-[9px] text-gray-600 uppercase tracking-wider">
          <span className="w-[100px]">Key</span>
          <span className="flex-1">Label</span>
          <span className="w-[80px]">Type</span>
          <span className="w-[36px]">Req</span>
        </div>
      )}

      {/* Field rows */}
      <div className="space-y-0">
        {fields.map((field, i) => (
          <FieldRow
            key={i}
            field={field}
            index={i}
            total={fields.length}
            onChange={(patch) => updateField(i, patch)}
            onMoveUp={() => moveUp(i)}
            onMoveDown={() => moveDown(i)}
            onRemove={() => removeField(i)}
            disabled={disabled}
          />
        ))}
      </div>

      {fields.length === 0 && (
        <div className="py-6 text-center">
          <p className="text-[11px] text-gray-600">No fields defined</p>
          {!disabled && (
            <button
              onClick={addField}
              className="mt-2 text-[11px] text-indigo-400 hover:text-indigo-300"
            >
              + Add your first field
            </button>
          )}
        </div>
      )}
    </div>
  );
}
