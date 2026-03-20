import { useAuthStore } from "@/stores/auth-store";
import { Shield, User, Key, Palette, Info } from "lucide-react";

function SettingsSection({
  icon: Icon,
  title,
  children,
}: {
  icon: React.ElementType;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-8 h-8 rounded-lg bg-indigo-600/10 flex items-center justify-center">
          <Icon className="w-4 h-4 text-indigo-400" />
        </div>
        <h2 className="text-base font-semibold text-white">{title}</h2>
      </div>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

function SettingsField({
  label,
  value,
  masked = false,
}: {
  label: string;
  value: string;
  masked?: boolean;
}) {
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

export function Settings() {
  const user = useAuthStore((s) => s.user);
  const email = user?.email ?? "";
  const initial = email ? email[0].toUpperCase() : "?";

  return (
    <div className="max-w-2xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-gray-400 mt-1">View your account and application configuration</p>
      </div>

      <div className="space-y-6">
        {/* Profile */}
        <SettingsSection icon={User} title="Profile">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-full bg-indigo-600/20 flex items-center justify-center text-indigo-400 text-lg font-semibold">
              {initial}
            </div>
            <div>
              <p className="text-sm text-white font-medium">{email || "Not signed in"}</p>
              <p className="text-xs text-gray-500">Authenticated via Supabase</p>
            </div>
          </div>
          <SettingsField label="Email" value={email} />
          <SettingsField label="User ID" value={user?.id ?? ""} />
        </SettingsSection>

        {/* API Keys */}
        <SettingsSection icon={Key} title="API Keys">
          <p className="text-xs text-gray-500 mb-2">
            API keys are configured via environment variables on the server.
          </p>
          <SettingsField label="DashScope API Key" value="configured" masked />
          <SettingsField label="OpenAI API Key" value="configured" masked />
        </SettingsSection>

        {/* Preferences */}
        <SettingsSection icon={Palette} title="Preferences">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Default VLM Provider</label>
            <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-300">
              DashScope (Qwen-VL)
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Theme</label>
            <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-300 flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#0a0a0f] border border-[#2a2a3a]" />
              Dark
            </div>
          </div>
        </SettingsSection>

        {/* About */}
        <SettingsSection icon={Info} title="About">
          <SettingsField label="Version" value="0.1.0-alpha" />
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">Stack</label>
            <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-300">
              FastAPI + React + LangGraph + Supabase
            </div>
          </div>
        </SettingsSection>

        {/* Security note */}
        <div className="flex items-start gap-3 px-4 py-3 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
          <Shield className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-gray-400">
            Settings are read-only in this view. Configuration changes should be made through
            environment variables or the server configuration.
          </p>
        </div>
      </div>
    </div>
  );
}
