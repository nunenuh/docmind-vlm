import { useState } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { Shield, User, Palette, Info } from "lucide-react";

type SettingsTab = "profile" | "preferences" | "about";

export function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");
  const user = useAuthStore((s) => s.user);
  const email = user?.email ?? "";
  const initial = email ? email[0].toUpperCase() : "?";

  const tabs: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
    { id: "profile", label: "Profile", icon: User },
    { id: "preferences", label: "Preferences", icon: Palette },
    { id: "about", label: "About", icon: Info },
  ];

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-gray-400 mt-1">Manage your account and preferences</p>
      </div>

      <div className="flex gap-2 mb-6 border-b border-[#1e1e2e] pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              activeTab === tab.id
                ? "bg-indigo-600/10 text-indigo-400"
                : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "profile" && <ProfileTab email={email} initial={initial} userId={user?.id ?? ""} />}
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
