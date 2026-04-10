import { Shield } from "lucide-react";

export function PreferencesSettings() {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-white">Preferences</h2>
        <p className="text-sm text-gray-400 mt-1">Application preferences and defaults</p>
      </div>
      <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
        <Field label="Default VLM Provider" value="DashScope (Qwen-VL)" />
        <Field label="Embedding Model" value="text-embedding-v4" />
        <Field label="Theme" value="Dark" />
        <div className="flex items-start gap-3 px-4 py-3 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
          <Shield className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-gray-400">
            Editable preferences coming in a future update.
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">{label}</label>
      <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-300">
        {value || "\u2014"}
      </div>
    </div>
  );
}
