import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { useCreateToken } from "@/hooks/useApiTokens";
import { ScopeCheckboxGrid } from "./ScopeCheckboxGrid";
import type { TokenCreatedResponse } from "@/types/api-token";

interface CreateTokenModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (response: TokenCreatedResponse) => void;
}

const EXPIRY_OPTIONS = [
  { label: "7 days", value: 7 },
  { label: "30 days", value: 30 },
  { label: "60 days", value: 60 },
  { label: "90 days", value: 90 },
  { label: "1 year", value: 365 },
  { label: "Never", value: null },
] as const;

export function CreateTokenModal({ isOpen, onClose, onCreated }: CreateTokenModalProps) {
  const [name, setName] = useState("");
  const [tokenType, setTokenType] = useState<"live" | "test">("live");
  const [scopes, setScopes] = useState<string[]>([]);
  const [expiresInDays, setExpiresInDays] = useState<number | null>(90);

  const createToken = useCreateToken();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || scopes.length === 0) return;

    try {
      const response = await createToken.mutateAsync({
        name: name.trim(),
        scopes: scopes as never[],
        token_type: tokenType,
        expires_in_days: expiresInDays,
      });
      onCreated(response);
      setName("");
      setScopes([]);
      setTokenType("live");
      setExpiresInDays(90);
    } catch {
      // Error handled by the hook
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#12121a] border border-[#1e1e2e] rounded-xl w-full max-w-xl max-h-[85vh] overflow-y-auto shadow-2xl mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e2e] sticky top-0 bg-[#12121a] z-10">
          <h2 className="text-lg font-semibold text-white">Create API Key</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Key Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Production Backend, CI/CD Pipeline"
              className="w-full bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 transition-colors"
              required
            />
          </div>

          {/* Token Type */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Environment
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setTokenType("live")}
                className={`flex-1 px-4 py-2.5 text-sm font-medium rounded-lg border transition-colors ${
                  tokenType === "live"
                    ? "bg-indigo-600/10 border-indigo-500 text-indigo-400"
                    : "bg-[#0a0a0f] border-[#1e1e2e] text-gray-400 hover:border-gray-700"
                }`}
              >
                Live
              </button>
              <button
                type="button"
                onClick={() => setTokenType("test")}
                className={`flex-1 px-4 py-2.5 text-sm font-medium rounded-lg border transition-colors ${
                  tokenType === "test"
                    ? "bg-amber-600/10 border-amber-500 text-amber-400"
                    : "bg-[#0a0a0f] border-[#1e1e2e] text-gray-400 hover:border-gray-700"
                }`}
              >
                Test
              </button>
            </div>
          </div>

          {/* Expiry */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Expiration
            </label>
            <select
              value={expiresInDays ?? "never"}
              onChange={(e) =>
                setExpiresInDays(
                  e.target.value === "never" ? null : Number(e.target.value)
                )
              }
              className="w-full bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
            >
              {EXPIRY_OPTIONS.map((opt) => (
                <option key={opt.label} value={opt.value ?? "never"}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Scopes */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Permissions
            </label>
            <ScopeCheckboxGrid selectedScopes={scopes} onChange={setScopes} />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white border border-[#1e1e2e] hover:border-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!name.trim() || scopes.length === 0 || createToken.isPending}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              {createToken.isPending && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              Create Key
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
