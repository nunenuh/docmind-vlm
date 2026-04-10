import { useAuthStore } from "@/stores/auth-store";

export function ProfileSettings() {
  const user = useAuthStore((s) => s.user);
  const email = user?.email ?? "";
  const initial = email ? email[0].toUpperCase() : "?";

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-white">Profile</h2>
        <p className="text-sm text-gray-400 mt-1">Your account information</p>
      </div>
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
        <Field label="User ID" value={user?.id ?? ""} />
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
