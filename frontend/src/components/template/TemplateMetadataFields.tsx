const CATEGORIES = [
  { value: "identity", label: "Identity" },
  { value: "government", label: "Government" },
  { value: "finance", label: "Finance" },
  { value: "legal", label: "Legal" },
  { value: "vehicle", label: "Vehicle" },
  { value: "tax", label: "Tax" },
  { value: "general", label: "General" },
  { value: "custom", label: "Custom" },
];

interface Props {
  name: string;
  onNameChange: (v: string) => void;
  type: string;
  onTypeChange: (v: string) => void;
  category: string;
  onCategoryChange: (v: string) => void;
  description: string;
  onDescriptionChange: (v: string) => void;
  extractionPrompt: string;
  onExtractionPromptChange: (v: string) => void;
  disabled?: boolean;
}

export function TemplateMetadataFields({
  name, onNameChange, type, onTypeChange, category, onCategoryChange,
  description, onDescriptionChange, extractionPrompt, onExtractionPromptChange,
  disabled,
}: Props) {
  const inputCls = "w-full px-3 py-2 text-[12px] bg-[#0B0D11] border border-white/[0.06] rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/30 disabled:opacity-50 transition-colors";

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">
            Name <span className="text-rose-400">*</span>
          </span>
          <input
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
            placeholder="e.g. KTP (Kartu Tanda Penduduk)"
            disabled={disabled}
            className={inputCls}
          />
        </label>
        <label className="block">
          <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">
            Type slug <span className="text-rose-400">*</span>
          </span>
          <input
            value={type}
            onChange={(e) => onTypeChange(e.target.value.toLowerCase().replace(/\s+/g, "_"))}
            placeholder="e.g. ktp"
            disabled={disabled}
            className={`${inputCls} font-mono`}
          />
        </label>
      </div>

      <label className="block">
        <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">Category</span>
        <select
          value={category}
          onChange={(e) => onCategoryChange(e.target.value)}
          disabled={disabled}
          className={inputCls}
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">Description</span>
        <textarea
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
          placeholder="Brief description of what this template extracts..."
          disabled={disabled}
          rows={2}
          className={`${inputCls} resize-none`}
        />
      </label>

      <label className="block">
        <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1 block">Extraction Prompt</span>
        <textarea
          value={extractionPrompt}
          onChange={(e) => onExtractionPromptChange(e.target.value)}
          placeholder="Instructions for the VLM on how to extract fields from this document type..."
          disabled={disabled}
          rows={4}
          className={`${inputCls} resize-none font-mono`}
        />
      </label>
    </div>
  );
}
