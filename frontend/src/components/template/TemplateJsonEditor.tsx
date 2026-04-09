import { AlertCircle, CheckCircle } from "lucide-react";

interface Props {
  value: string;
  onChange: (value: string) => void;
  error: string | null;
}

export function TemplateJsonEditor({ value, onChange, error }: Props) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wider">
          Fields JSON
        </span>
        {error ? (
          <span className="flex items-center gap-1 text-[10px] text-rose-400">
            <AlertCircle className="w-3 h-3" />
            {error}
          </span>
        ) : value.trim() ? (
          <span className="flex items-center gap-1 text-[10px] text-emerald-400">
            <CheckCircle className="w-3 h-3" />
            Valid JSON
          </span>
        ) : null}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={18}
        spellCheck={false}
        className={`w-full px-3 py-2.5 text-[11px] font-mono leading-relaxed bg-[#0B0D11] border rounded-lg text-gray-200 placeholder-gray-700 outline-none resize-none transition-colors ${
          error ? "border-rose-500/30" : "border-white/[0.06] focus:border-indigo-500/30"
        }`}
        placeholder={`[\n  {\n    "key": "field_name",\n    "label": "Field Label",\n    "type": "string",\n    "required": true\n  }\n]`}
      />
    </div>
  );
}
