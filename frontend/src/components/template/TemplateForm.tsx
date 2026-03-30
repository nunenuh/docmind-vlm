import { useState, useEffect } from "react";
import { Loader2, Code, FormInput } from "lucide-react";
import { useTemplateDetail, useCreateTemplate, useUpdateTemplate } from "@/hooks/useTemplates";
import { TemplateMetadataFields } from "./TemplateMetadataFields";
import { TemplateFieldEditor } from "./TemplateFieldEditor";
import { TemplateJsonEditor } from "./TemplateJsonEditor";
import type { TemplateFieldDef } from "@/types/api";

interface Props {
  templateId?: string;
  onClose: () => void;
  onSaved?: () => void;
}

export function TemplateForm({ templateId, onClose, onSaved }: Props) {
  const isEdit = !!templateId;
  const { data: existing, isLoading } = useTemplateDetail(templateId ?? "");
  const createMutation = useCreateTemplate();
  const updateMutation = useUpdateTemplate();

  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [category, setCategory] = useState("custom");
  const [description, setDescription] = useState("");
  const [extractionPrompt, setExtractionPrompt] = useState("");
  const [fields, setFields] = useState<TemplateFieldDef[]>([]);
  const [editorMode, setEditorMode] = useState<"form" | "json">("form");
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  // Populate form when editing
  useEffect(() => {
    if (isEdit && existing && !initialized) {
      setName(existing.name);
      setType(existing.type);
      setCategory(existing.category || "custom");
      setDescription(existing.description || "");
      setExtractionPrompt(existing.extraction_prompt || "");
      setFields(existing.fields || []);
      setJsonText(JSON.stringify(existing.fields || [], null, 2));
      setInitialized(true);
    }
  }, [isEdit, existing, initialized]);

  // Sync fields → JSON when switching to JSON mode
  const switchToJson = () => {
    setJsonText(JSON.stringify(fields, null, 2));
    setJsonError(null);
    setEditorMode("json");
  };

  // Sync JSON → fields when switching to form mode
  const switchToForm = () => {
    if (jsonText.trim()) {
      try {
        const parsed = JSON.parse(jsonText);
        if (!Array.isArray(parsed)) {
          setJsonError("Must be an array of fields");
          return;
        }
        setFields(parsed);
        setJsonError(null);
      } catch {
        setJsonError("Invalid JSON — fix before switching");
        return;
      }
    }
    setEditorMode("form");
  };

  const handleJsonChange = (value: string) => {
    setJsonText(value);
    if (!value.trim()) {
      setJsonError(null);
      return;
    }
    try {
      const parsed = JSON.parse(value);
      if (!Array.isArray(parsed)) {
        setJsonError("Must be an array");
      } else {
        setJsonError(null);
      }
    } catch {
      setJsonError("Invalid JSON");
    }
  };

  const handleSubmit = () => {
    // Resolve fields from current mode
    let finalFields = fields;
    if (editorMode === "json" && jsonText.trim()) {
      try {
        finalFields = JSON.parse(jsonText);
      } catch {
        setJsonError("Fix JSON before saving");
        return;
      }
    }

    const payload = {
      name,
      type,
      category,
      description: description || undefined,
      extraction_prompt: extractionPrompt || undefined,
      fields: finalFields,
    };

    if (isEdit && templateId) {
      updateMutation.mutate({ id: templateId, data: payload }, {
        onSuccess: () => { onSaved?.(); onClose(); },
      });
    } else {
      createMutation.mutate(payload, {
        onSuccess: () => { onSaved?.(); onClose(); },
      });
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;
  const canSubmit = name.trim() && type.trim() && !jsonError && !isPending;

  if (isEdit && isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        {/* Metadata */}
        <TemplateMetadataFields
          name={name} onNameChange={setName}
          type={type} onTypeChange={setType}
          category={category} onCategoryChange={setCategory}
          description={description} onDescriptionChange={setDescription}
          extractionPrompt={extractionPrompt} onExtractionPromptChange={setExtractionPrompt}
        />

        {/* Divider */}
        <div className="border-t border-white/[0.05]" />

        {/* Mode toggle */}
        <div className="flex items-center gap-1 bg-white/[0.03] rounded-lg p-0.5 w-fit">
          <button
            onClick={editorMode === "json" ? switchToForm : undefined}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-md transition-all ${
              editorMode === "form"
                ? "bg-white/[0.06] text-gray-200"
                : "text-gray-500 hover:text-gray-400"
            }`}
          >
            <FormInput className="w-3 h-3" />
            Form
          </button>
          <button
            onClick={editorMode === "form" ? switchToJson : undefined}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-md transition-all ${
              editorMode === "json"
                ? "bg-white/[0.06] text-gray-200"
                : "text-gray-500 hover:text-gray-400"
            }`}
          >
            <Code className="w-3 h-3" />
            JSON
          </button>
        </div>

        {/* Field editor */}
        {editorMode === "form" ? (
          <TemplateFieldEditor fields={fields} onChange={setFields} />
        ) : (
          <TemplateJsonEditor value={jsonText} onChange={handleJsonChange} error={jsonError} />
        )}
      </div>

      {/* Footer actions */}
      <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-white/[0.05] flex-shrink-0">
        <button
          onClick={onClose}
          className="px-4 py-2 text-[12px] font-medium text-gray-400 hover:text-gray-200 rounded-lg hover:bg-white/[0.04] transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="flex items-center gap-2 px-4 py-2 text-[12px] font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          {isEdit ? "Save Changes" : "Create Template"}
        </button>
      </div>
    </div>
  );
}
