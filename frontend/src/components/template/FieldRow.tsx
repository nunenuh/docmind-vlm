import { ChevronUp, ChevronDown, Trash2, Plus, X } from "lucide-react";
import type { TemplateFieldDef } from "@/types/api";

const FIELD_TYPES = ["string", "date", "enum", "table", "number", "boolean"];

interface Props {
  field: TemplateFieldDef;
  index: number;
  total: number;
  onChange: (patch: Partial<TemplateFieldDef>) => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onRemove: () => void;
  disabled?: boolean;
}

export function FieldRow({ field, index, total, onChange, onMoveUp, onMoveDown, onRemove, disabled }: Props) {
  return (
    <div className="group">
      <div className="flex items-center gap-1.5 py-1.5">
        {/* Key */}
        <input
          value={field.key}
          onChange={(e) => onChange({ key: e.target.value })}
          placeholder="field_key"
          disabled={disabled}
          className="w-[100px] px-2 py-1.5 text-[11px] font-mono bg-[#0B0D11] border border-white/[0.06] rounded text-gray-200 placeholder-gray-700 outline-none focus:border-indigo-500/30 disabled:opacity-50"
        />
        {/* Label */}
        <input
          value={field.label}
          onChange={(e) => onChange({ label: e.target.value })}
          placeholder="Label"
          disabled={disabled}
          className="flex-1 min-w-0 px-2 py-1.5 text-[11px] bg-[#0B0D11] border border-white/[0.06] rounded text-gray-200 placeholder-gray-700 outline-none focus:border-indigo-500/30 disabled:opacity-50"
        />
        {/* Type */}
        <select
          value={field.type}
          onChange={(e) => onChange({ type: e.target.value })}
          disabled={disabled}
          className="w-[80px] px-1.5 py-1.5 text-[11px] bg-[#0B0D11] border border-white/[0.06] rounded text-gray-300 outline-none focus:border-indigo-500/30 disabled:opacity-50"
        >
          {FIELD_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        {/* Required toggle */}
        <button
          onClick={() => onChange({ required: !field.required })}
          disabled={disabled}
          className={`px-2 py-1.5 text-[10px] font-medium rounded transition-colors ${
            field.required
              ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/20"
              : "bg-white/[0.03] text-gray-600 border border-white/[0.06]"
          } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:opacity-80"}`}
        >
          {field.required ? "Req" : "Opt"}
        </button>
        {/* Actions */}
        {!disabled && (
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={onMoveUp}
              disabled={index === 0}
              className="p-1 text-gray-600 hover:text-gray-400 rounded disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronUp className="w-3 h-3" />
            </button>
            <button
              onClick={onMoveDown}
              disabled={index === total - 1}
              className="p-1 text-gray-600 hover:text-gray-400 rounded disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronDown className="w-3 h-3" />
            </button>
            <button
              onClick={onRemove}
              className="p-1 text-gray-600 hover:text-rose-400 rounded"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>

      {/* Enum values editor */}
      {field.type === "enum" && (
        <EnumValuesEditor
          values={field.values ?? []}
          onChange={(values) => onChange({ values })}
          disabled={disabled}
        />
      )}
    </div>
  );
}

/* ── Enum Values Editor ───────────────── */

function EnumValuesEditor({ values, onChange, disabled }: {
  values: string[];
  onChange: (values: string[]) => void;
  disabled?: boolean;
}) {
  const handleAdd = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || values.includes(trimmed)) return;
    onChange([...values, trimmed]);
  };

  const handleRemove = (index: number) => {
    onChange(values.filter((_, i) => i !== index));
  };

  return (
    <div className="ml-[108px] pb-2 flex flex-wrap items-center gap-1">
      {values.map((v, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] bg-indigo-500/10 text-indigo-300 rounded-full"
        >
          {v}
          {!disabled && (
            <button onClick={() => handleRemove(i)} className="hover:text-rose-400">
              <X className="w-2.5 h-2.5" />
            </button>
          )}
        </span>
      ))}
      {!disabled && (
        <input
          placeholder="+ value"
          className="w-[70px] px-1.5 py-0.5 text-[10px] bg-transparent border-b border-white/[0.06] text-gray-400 placeholder-gray-700 outline-none focus:border-indigo-500/30"
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleAdd(e.currentTarget.value);
              e.currentTarget.value = "";
            }
          }}
        />
      )}
    </div>
  );
}
