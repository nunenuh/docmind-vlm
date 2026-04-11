import { useState, useEffect } from "react";
import { X, Loader2, RefreshCw } from "lucide-react";
import { useUpdateToken, useRegenerateToken } from "@/hooks/useApiTokens";
import { ScopeCheckboxGrid } from "./ScopeCheckboxGrid";
import type { TokenResponse, TokenCreatedResponse } from "@/types/api-token";

interface EditTokenModalProps {
  isOpen: boolean;
  token: TokenResponse | null;
  onClose: () => void;
  onRegenerated?: (newToken: TokenCreatedResponse) => void;
}

export function EditTokenModal({ isOpen, token, onClose, onRegenerated }: EditTokenModalProps) {
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>([]);
  const [showRegenerateConfirm, setShowRegenerateConfirm] = useState(false);

  const updateToken = useUpdateToken();
  const regenerateToken = useRegenerateToken();

  useEffect(() => {
    if (token) {
      setName(token.name);
      setScopes([...token.scopes]);
      setShowRegenerateConfirm(false);
    }
  }, [token]);

  const handleRegenerate = async () => {
    if (!token) return;
    try {
      const newToken = await regenerateToken.mutateAsync(token.id);
      onClose();
      onRegenerated?.(newToken);
    } catch {
      // Error handled by the hook
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !name.trim() || scopes.length === 0) return;

    try {
      await updateToken.mutateAsync({
        id: token.id,
        data: {
          name: name.trim(),
          scopes: scopes as never[],
        },
      });
      onClose();
    } catch {
      // Error handled by the hook
    }
  };

  if (!isOpen || !token) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#12121a] border border-[#1e1e2e] rounded-xl w-full max-w-xl max-h-[85vh] overflow-y-auto shadow-2xl mx-4">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e2e] sticky top-0 bg-[#12121a] z-10">
          <h2 className="text-lg font-semibold text-white">Edit API Key</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          {/* Prefix (read-only) */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Key Prefix
            </label>
            <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-500 font-mono">
              {token.prefix}...
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Key Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 transition-colors"
              required
            />
          </div>

          {/* Scopes */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Permissions
            </label>
            <ScopeCheckboxGrid selectedScopes={scopes} onChange={setScopes} />
          </div>

          {/* Regenerate */}
          <div className="border border-amber-500/20 bg-amber-500/5 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-sm font-medium text-amber-300 flex items-center gap-1.5">
                  <RefreshCw className="w-3.5 h-3.5" />
                  Regenerate Key
                </h4>
                <p className="text-xs text-gray-400 mt-1">
                  Create a new secret key. The current key will be revoked immediately.
                </p>
              </div>
              {!showRegenerateConfirm ? (
                <button
                  type="button"
                  onClick={() => setShowRegenerateConfirm(true)}
                  className="px-3 py-1.5 text-xs font-medium text-amber-300 border border-amber-500/30 hover:bg-amber-500/10 rounded-lg transition-colors shrink-0"
                >
                  Regenerate
                </button>
              ) : (
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => setShowRegenerateConfirm(false)}
                    className="px-3 py-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={handleRegenerate}
                    disabled={regenerateToken.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg transition-colors"
                  >
                    {regenerateToken.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                    Confirm Regenerate
                  </button>
                </div>
              )}
            </div>
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
              disabled={!name.trim() || scopes.length === 0 || updateToken.isPending}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
            >
              {updateToken.isPending && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
