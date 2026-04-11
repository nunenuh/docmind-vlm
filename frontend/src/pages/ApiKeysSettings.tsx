import { useState } from "react";
import { Plus, Loader2, AlertCircle } from "lucide-react";
import { useTokens, useRevokeToken, useRegenerateToken } from "@/hooks/useApiTokens";
import { TokenList } from "@/components/settings/TokenList";
import { CreateTokenModal } from "@/components/settings/CreateTokenModal";
import { TokenCreatedView } from "@/components/settings/TokenCreatedView";
import { EditTokenModal } from "@/components/settings/EditTokenModal";
import { RevokeTokenDialog } from "@/components/settings/RevokeTokenDialog";
import type { TokenResponse, TokenCreatedResponse } from "@/types/api-token";

export function ApiKeysSettings() {
  const { data, isLoading, isError, error } = useTokens();
  const revokeToken = useRevokeToken();
  const regenerateToken = useRegenerateToken();

  const [showCreate, setShowCreate] = useState(false);
  const [createdToken, setCreatedToken] = useState<TokenCreatedResponse | null>(null);
  const [editingToken, setEditingToken] = useState<TokenResponse | null>(null);
  const [revokingToken, setRevokingToken] = useState<TokenResponse | null>(null);

  const handleCreated = (response: TokenCreatedResponse) => {
    setShowCreate(false);
    setCreatedToken(response);
  };

  const handleRevokeConfirm = () => {
    if (revokingToken) {
      revokeToken.mutate(revokingToken.id);
      setRevokingToken(null);
    }
  };

  const tokens = data?.tokens ?? [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">API Keys</h2>
          <p className="text-sm text-gray-400 mt-1">
            Create and manage API keys for programmatic access
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/20"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading API keys...</p>
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="w-8 h-8 text-red-400 mb-3" />
          <p className="text-sm text-red-400">
            Failed to load API keys: {(error as Error)?.message ?? "Unknown error"}
          </p>
        </div>
      ) : (
        <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl">
          <TokenList
            tokens={tokens}
            onEdit={setEditingToken}
            onRevoke={setRevokingToken}
            onRegenerate={(token) => {
              if (confirm(`Regenerate "${token.name}"? The old key will be revoked immediately.`)) {
                regenerateToken.mutate(token.id, {
                  onSuccess: (newToken) => setCreatedToken(newToken),
                });
              }
            }}
          />
        </div>
      )}

      {/* Modals */}
      <CreateTokenModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={handleCreated}
      />

      {createdToken && (
        <TokenCreatedView
          token={createdToken}
          onClose={() => setCreatedToken(null)}
        />
      )}

      <EditTokenModal
        isOpen={!!editingToken}
        token={editingToken}
        onClose={() => setEditingToken(null)}
      />

      <RevokeTokenDialog
        isOpen={!!revokingToken}
        token={revokingToken}
        onClose={() => setRevokingToken(null)}
        onConfirm={handleRevokeConfirm}
      />
    </div>
  );
}
