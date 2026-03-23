import { useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { Shield, User, Key, Palette, Info, FileText, Tag, Copy, Trash2, Plus, Loader2 } from "lucide-react";
import { useTemplates, useDeleteTemplate, useDuplicateTemplate } from "@/hooks/useTemplates";
import type { TemplateSummary } from "@/types/api";

type SettingsTab = "profile" | "templates" | "preferences" | "about";

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
    { id: "preferences", label: "Preferences", icon: Palette },
    { id: "about", label: "About", icon: Info },
  ];

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-gray-400 mt-1">Manage your account, templates, and preferences</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-[#1e1e2e] pb-px">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-t-lg transition-colors relative ${
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

      {/* Tab content */}
      {activeTab === "profile" && <ProfileTab email={email} initial={initial} userId={user?.id ?? ""} />}
      {activeTab === "templates" && <TemplatesTab />}
      {activeTab === "preferences" && <PreferencesTab />}
      {activeTab === "about" && <AboutTab />}
    </div>
  );
}

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
      <SettingsField label="Email" value={email} />
      <SettingsField label="User ID" value={userId} />
    </div>
  );
}

function TemplatesTab() {
  const { data, isLoading } = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const duplicateTemplate = useDuplicateTemplate();

  const templates = data?.items ?? [];
  const presets = templates.filter((t) => t.is_preset);
  const custom = templates.filter((t) => !t.is_preset);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Info */}
      <div className="flex items-start gap-3 px-4 py-3 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
        <FileText className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-gray-400">
          Templates define which fields to extract from documents. Preset templates are read-only —
          duplicate them to customize. When processing a document, you can select a template or let AI auto-detect.
        </p>
      </div>

      {/* Preset templates */}
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
          <Tag className="w-4 h-4 text-gray-500" />
          Preset Templates ({presets.length})
        </h3>
        <div className="grid sm:grid-cols-2 gap-2">
          {presets.map((t) => (
            <TemplateCard
              key={t.id}
              template={t}
              onDuplicate={() => duplicateTemplate.mutate(t.id)}
            />
          ))}
        </div>
      </div>

      {/* Custom templates */}
      <div>
        <h3 className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
          <Plus className="w-4 h-4 text-gray-500" />
          Custom Templates ({custom.length})
        </h3>
        {custom.length === 0 ? (
          <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-8 text-center">
            <p className="text-sm text-gray-500">No custom templates yet</p>
            <p className="text-xs text-gray-600 mt-1">Duplicate a preset to customize, or process a document to auto-generate</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-2">
            {custom.map((t) => (
              <TemplateCard
                key={t.id}
                template={t}
                onDelete={() => {
                  if (window.confirm(`Delete "${t.name}"?`)) {
                    deleteTemplate.mutate(t.id);
                  }
                }}
                onDuplicate={() => duplicateTemplate.mutate(t.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TemplateCard({
  template,
  onDelete,
  onDuplicate,
}: {
  template: TemplateSummary;
  onDelete?: () => void;
  onDuplicate?: () => void;
}) {
  return (
    <div className="group bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4 hover:border-[#2a2a3a] transition-colors">
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0">
          <h4 className="text-sm text-white font-medium truncate">{template.name}</h4>
          {template.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{template.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
          {onDuplicate && (
            <button
              onClick={onDuplicate}
              className="p-1.5 text-gray-500 hover:text-indigo-400 rounded-md hover:bg-indigo-500/10 transition-colors"
              title="Duplicate"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="p-1.5 text-gray-500 hover:text-rose-400 rounded-md hover:bg-rose-500/10 transition-colors"
              title="Delete"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${CATEGORY_COLORS[template.category] || CATEGORY_COLORS.general}`}>
          {template.category}
        </span>
        <span className="text-xs text-gray-600">
          {template.required_field_count} required + {template.optional_field_count} optional
        </span>
        {template.is_preset && (
          <Tag className="w-3 h-3 text-gray-600 ml-auto" />
        )}
      </div>
    </div>
  );
}

function PreferencesTab() {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
      <SettingsField label="Default VLM Provider" value="DashScope (Qwen-VL)" />
      <SettingsField label="Embedding Model" value="text-embedding-v4" />
      <SettingsField label="Theme" value="Dark" />
      <div className="flex items-start gap-3 px-4 py-3 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
        <Shield className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
        <p className="text-xs text-gray-400">
          Settings are configured via environment variables. Editable preferences coming soon.
        </p>
      </div>
    </div>
  );
}

function AboutTab() {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
      <SettingsField label="Version" value="0.1.0-alpha" />
      <SettingsField label="Stack" value="FastAPI + React + LangGraph + Supabase + pgvector" />
      <SettingsField label="VLM" value="Qwen-VL via DashScope (primary)" />
      <SettingsField label="RAG" value="pymupdf4llm + text-embedding-v4 + pgvector" />
    </div>
  );
}

function SettingsField({ label, value, masked = false }: { label: string; value: string; masked?: boolean }) {
  const displayValue = masked && value ? "\u2022".repeat(12) : value || "\u2014";
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">{label}</label>
      <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-300">
        {displayValue}
      </div>
    </div>
  );
}
