import { useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import {
  Shield, User, Key, Palette, Info, FileText, Tag, Copy, Trash2, Plus,
  Loader2, X, Bot, ChevronDown, ChevronUp, Code, FormInput,
} from "lucide-react";
import { toast } from "sonner";
import { useTemplates, useDeleteTemplate, useDuplicateTemplate, useCreateTemplate } from "@/hooks/useTemplates";
import { usePersonas } from "@/hooks/usePersonas";
import type { TemplateSummary, PersonaResponse } from "@/types/api";

type SettingsTab = "profile" | "templates" | "personas" | "preferences" | "about";

const CATEGORY_COLORS: Record<string, string> = {
  identity: "text-blue-400 bg-blue-400/10",
  vehicle: "text-emerald-400 bg-emerald-400/10",
  tax: "text-amber-400 bg-amber-400/10",
  finance: "text-violet-400 bg-violet-400/10",
  legal: "text-rose-400 bg-rose-400/10",
  general: "text-gray-400 bg-gray-400/10",
  custom: "text-indigo-400 bg-indigo-400/10",
};

export function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const user = useAuthStore((s) => s.user);
  const email = user?.email ?? "";
  const initial = email ? email[0].toUpperCase() : "?";

  const tabs: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
    { id: "profile", label: "Profile", icon: User },
    { id: "templates", label: "Templates", icon: FileText },
    { id: "personas", label: "Personas", icon: Bot },
    { id: "preferences", label: "Preferences", icon: Palette },
    { id: "about", label: "About", icon: Info },
  ];

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-gray-400 mt-1">Manage your account, templates, personas, and preferences</p>
      </div>

      <div className="flex gap-1 mb-6 border-b border-[#1e1e2e] pb-px overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors whitespace-nowrap relative ${
              activeTab === tab.id
                ? "text-white bg-[#12121a] border border-[#1e1e2e] border-b-transparent -mb-px"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "profile" && <ProfileTab email={email} initial={initial} userId={user?.id ?? ""} />}
      {activeTab === "templates" && <TemplatesTab />}
      {activeTab === "personas" && <PersonasTab />}
      {activeTab === "preferences" && <PreferencesTab />}
      {activeTab === "about" && <AboutTab />}
    </div>
  );
}

// ── Templates Tab ──────────────────────────────────────

function TemplatesTab() {
  const { data, isLoading } = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const duplicateTemplate = useDuplicateTemplate();
  const [showCreate, setShowCreate] = useState(false);

  const templates = data?.items ?? [];
  const presets = templates.filter((t) => t.is_preset);
  const custom = templates.filter((t) => !t.is_preset);

  if (isLoading) {
    return <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-indigo-400 animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">
          {templates.length} templates ({presets.length} presets, {custom.length} custom)
        </p>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Template
        </button>
      </div>

      {/* Preset templates */}
      {presets.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
            <Tag className="w-4 h-4 text-gray-500" />
            Preset Templates ({presets.length})
          </h3>
          <div className="grid sm:grid-cols-2 gap-2">
            {presets.map((t) => (
              <TemplateCard key={t.id} template={t} onDuplicate={() => duplicateTemplate.mutate(t.id)} />
            ))}
          </div>
        </div>
      )}

      {presets.length === 0 && (
        <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-6 text-center">
          <p className="text-sm text-gray-400">No preset templates loaded</p>
          <p className="text-xs text-gray-600 mt-1">They will auto-seed when the backend starts</p>
        </div>
      )}

      {/* Custom templates */}
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
          <Plus className="w-4 h-4 text-gray-500" />
          Custom Templates ({custom.length})
        </h3>
        {custom.length === 0 ? (
          <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-6 text-center">
            <p className="text-sm text-gray-500">No custom templates yet</p>
            <p className="text-xs text-gray-600 mt-1">Click "Create Template" or duplicate a preset to customize</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-2">
            {custom.map((t) => (
              <TemplateCard
                key={t.id}
                template={t}
                onDelete={() => { if (window.confirm(`Delete "${t.name}"?`)) deleteTemplate.mutate(t.id); }}
                onDuplicate={() => duplicateTemplate.mutate(t.id)}
              />
            ))}
          </div>
        )}
      </div>

      {showCreate && <CreateTemplateModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function CreateTemplateModal({ onClose }: { onClose: () => void }) {
  const createTemplate = useCreateTemplate();
  const [mode, setMode] = useState<"form" | "json">("form");
  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [category, setCategory] = useState("custom");
  const [description, setDescription] = useState("");
  const [jsonText, setJsonText] = useState(JSON.stringify({
    type: "my_template",
    name: "My Template",
    category: "custom",
    fields: [
      { key: "field_1", label: "Field 1", type: "string", required: true },
      { key: "field_2", label: "Field 2", type: "string", required: false },
    ],
    extraction_prompt: "Extract the following fields from this document...",
  }, null, 2));
  const [jsonError, setJsonError] = useState<string | null>(null);

  const handleSubmitForm = () => {
    if (!name.trim() || !type.trim()) {
      toast.error("Name and type are required");
      return;
    }
    createTemplate.mutate({
      type: type.trim(),
      name: name.trim(),
      category,
      description: description.trim() || undefined,
      fields: [],
      extraction_prompt: "",
    }, { onSuccess: () => onClose() });
  };

  const handleSubmitJson = () => {
    try {
      const parsed = JSON.parse(jsonText);
      setJsonError(null);
      createTemplate.mutate({
        type: parsed.type || "custom",
        name: parsed.name || "Custom Template",
        category: parsed.category || "custom",
        description: parsed.description,
        fields: parsed.fields || [],
        extraction_prompt: parsed.extraction_prompt || "",
      }, { onSuccess: () => onClose() });
    } catch (e) {
      setJsonError(`Invalid JSON: ${(e as Error).message}`);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#12121a] border border-[#1e1e2e] rounded-2xl w-full max-w-2xl mx-4 shadow-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e2e]">
          <h2 className="text-lg font-semibold text-white">Create Template</h2>
          <button onClick={onClose} className="p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-white/5">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode toggle */}
        <div className="flex gap-1 px-6 pt-4">
          <button
            onClick={() => setMode("form")}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              mode === "form" ? "bg-indigo-500/20 text-indigo-300" : "text-gray-500 hover:text-gray-300"
            }`}
          >
            <FormInput className="w-3.5 h-3.5" />
            Visual Editor
          </button>
          <button
            onClick={() => setMode("json")}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              mode === "json" ? "bg-indigo-500/20 text-indigo-300" : "text-gray-500 hover:text-gray-300"
            }`}
          >
            <Code className="w-3.5 h-3.5" />
            JSON Editor
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {mode === "form" ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Template Type *</label>
                  <input
                    value={type}
                    onChange={(e) => setType(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_"))}
                    placeholder="e.g., ktp, invoice_custom"
                    className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Display Name *</label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Custom Invoice"
                    className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="custom">Custom</option>
                  <option value="identity">Identity</option>
                  <option value="finance">Finance</option>
                  <option value="tax">Tax</option>
                  <option value="legal">Legal</option>
                  <option value="vehicle">Vehicle</option>
                  <option value="general">General</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Description</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of what this template extracts..."
                  rows={2}
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-indigo-500"
                />
              </div>
              <p className="text-xs text-gray-500">
                Fields can be added after creation by editing the template, or switch to JSON mode to define fields now.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-gray-500">
                Paste or edit the JSON template definition. Must include "type", "name", and "fields" array.
              </p>
              <textarea
                value={jsonText}
                onChange={(e) => { setJsonText(e.target.value); setJsonError(null); }}
                className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-4 py-3 text-sm text-gray-200 font-mono resize-none focus:outline-none focus:border-indigo-500 leading-relaxed"
                rows={16}
                spellCheck={false}
              />
              {jsonError && (
                <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2">
                  {jsonError}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#1e1e2e]">
          <button onClick={onClose} className="px-4 py-2.5 text-sm text-gray-400 hover:text-white rounded-lg hover:bg-white/5">
            Cancel
          </button>
          <button
            onClick={mode === "form" ? handleSubmitForm : handleSubmitJson}
            disabled={createTemplate.isPending}
            className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {createTemplate.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Create Template
          </button>
        </div>
      </div>
    </div>
  );
}

function TemplateCard({ template, onDelete, onDuplicate }: { template: TemplateSummary; onDelete?: () => void; onDuplicate?: () => void }) {
  return (
    <div className="group bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4 hover:border-[#2a2a3a] transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0">
          <h4 className="text-sm text-white font-medium truncate">{template.name}</h4>
          {template.description && <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{template.description}</p>}
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
          {onDuplicate && (
            <button onClick={onDuplicate} className="p-1.5 text-gray-500 hover:text-indigo-400 rounded-md hover:bg-indigo-500/10" title="Duplicate">
              <Copy className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button onClick={onDelete} className="p-1.5 text-gray-500 hover:text-rose-400 rounded-md hover:bg-rose-500/10" title="Delete">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${CATEGORY_COLORS[template.category] || CATEGORY_COLORS.general}`}>
          {template.category}
        </span>
        <span className="text-xs text-gray-600">{template.total_field_count} fields</span>
        {template.is_preset && <Tag className="w-3 h-3 text-gray-600 ml-auto" />}
      </div>
    </div>
  );
}

// ── Personas Tab ──────────────────────────────────────

function PersonasTab() {
  const { data, isLoading } = usePersonas();
  const personas = data ?? [];
  const presets = personas.filter((p: PersonaResponse) => p.is_preset);
  const custom = personas.filter((p: PersonaResponse) => !p.is_preset);

  if (isLoading) {
    return <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-indigo-400 animate-spin" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-3 px-4 py-3 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
        <Bot className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-gray-400">
          Personas define how the AI responds in project chats. Each project can have one persona.
          Presets are system-provided; create custom personas for specific use cases.
        </p>
      </div>

      {presets.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-300 mb-3">Preset Personas ({presets.length})</h3>
          <div className="grid sm:grid-cols-2 gap-2">
            {presets.map((p: PersonaResponse) => <PersonaCard key={p.id} persona={p} />)}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3">Custom Personas ({custom.length})</h3>
        {custom.length === 0 ? (
          <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-6 text-center">
            <p className="text-sm text-gray-500">No custom personas yet</p>
            <p className="text-xs text-gray-600 mt-1">Create one from the project settings</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-2">
            {custom.map((p: PersonaResponse) => <PersonaCard key={p.id} persona={p} />)}
          </div>
        )}
      </div>
    </div>
  );
}

function PersonaCard({ persona }: { persona: PersonaResponse }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h4 className="text-sm text-white font-medium truncate">{persona.name}</h4>
            {persona.is_preset && <Tag className="w-3 h-3 text-gray-600" />}
          </div>
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{persona.description}</p>
        </div>
      </div>
      {persona.system_prompt && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 mt-3 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          System prompt
        </button>
      )}
      {expanded && persona.system_prompt && (
        <pre className="mt-2 text-xs text-gray-500 bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg p-3 max-h-32 overflow-y-auto whitespace-pre-wrap font-mono">
          {persona.system_prompt}
        </pre>
      )}
    </div>
  );
}

// ── Other Tabs ──────────────────────────────────────

function ProfileTab({ email, initial, userId }: { email: string; initial: string; userId: string }) {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
      <div className="flex items-center gap-4 mb-4">
        <div className="w-14 h-14 rounded-full bg-indigo-600/20 flex items-center justify-center text-indigo-400 text-xl font-semibold">
          {initial}
        </div>
        <div>
          <p className="text-sm text-white font-medium">{email || "Not signed in"}</p>
          <p className="text-xs text-gray-500">Authenticated via Supabase</p>
        </div>
      </div>
      <Field label="Email" value={email} />
      <Field label="User ID" value={userId} />
    </div>
  );
}

function PreferencesTab() {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
      <Field label="Default VLM Provider" value="DashScope (Qwen-VL)" />
      <Field label="Embedding Model" value="text-embedding-v4" />
      <Field label="Theme" value="Dark" />
      <div className="flex items-start gap-3 px-4 py-3 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
        <Shield className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-gray-400">Editable preferences coming in a future update.</p>
      </div>
    </div>
  );
}

function AboutTab() {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
      <Field label="Version" value="0.2.0-alpha" />
      <Field label="Stack" value="FastAPI + React + LangGraph + Supabase + pgvector" />
      <Field label="VLM" value="Qwen-VL via DashScope" />
      <Field label="RAG" value="pymupdf4llm + text-embedding-v4 + pgvector + hybrid search" />
      <Field label="Templates" value="15 Indonesian document templates + custom" />
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">{label}</label>
      <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-300">{value || "\u2014"}</div>
    </div>
  );
}
