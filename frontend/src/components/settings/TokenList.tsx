import { Edit, Trash2, Key } from "lucide-react";
import type { TokenResponse } from "@/types/api-token";

interface TokenListProps {
  tokens: TokenResponse[];
  onEdit: (token: TokenResponse) => void;
  onRevoke: (token: TokenResponse) => void;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "\u2014";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getExpiryStatus(expiresAt: string | null): {
  label: string;
  className: string;
} {
  if (!expiresAt) return { label: "Never expires", className: "text-gray-500" };
  const now = new Date();
  const exp = new Date(expiresAt);
  const daysLeft = Math.ceil((exp.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (daysLeft < 0) return { label: "Expired", className: "text-red-400" };
  if (daysLeft <= 7) return { label: `${daysLeft}d left`, className: "text-amber-400" };
  return { label: formatDate(expiresAt), className: "text-gray-400" };
}

function ScopeBadge({ scope }: { scope: string }) {
  return (
    <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
      {scope}
    </span>
  );
}

function TypeBadge({ type }: { type: string }) {
  const isLive = type === "live";
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs rounded-full border ${
        isLive
          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
      }`}
    >
      {type}
    </span>
  );
}

export function TokenList({ tokens, onEdit, onRevoke }: TokenListProps) {
  if (tokens.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4">
          <Key className="w-8 h-8 text-indigo-400" />
        </div>
        <h3 className="text-lg font-semibold text-white mb-1">No API keys yet</h3>
        <p className="text-sm text-gray-500 text-center max-w-sm">
          Create one to get started with programmatic access to the DocMind API.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[#1e1e2e]">
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Name
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Prefix
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Scopes
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Created
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Last Used
            </th>
            <th className="text-left py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Expires
            </th>
            <th className="text-right py-3 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {tokens.map((token) => {
            const expiry = getExpiryStatus(token.expires_at);
            const isRevoked = !!token.revoked_at;
            return (
              <tr
                key={token.id}
                className={`border-b border-[#1e1e2e] hover:bg-white/[0.02] transition-colors ${
                  isRevoked ? "opacity-50" : ""
                }`}
              >
                <td className="py-3 px-4">
                  <span className="text-white font-medium">{token.name}</span>
                </td>
                <td className="py-3 px-4">
                  <code className="text-gray-400 font-mono text-xs">
                    {token.prefix}...
                  </code>
                </td>
                <td className="py-3 px-4">
                  <div className="flex flex-wrap gap-1 max-w-xs">
                    {token.scopes.slice(0, 3).map((scope) => (
                      <ScopeBadge key={scope} scope={scope} />
                    ))}
                    {token.scopes.length > 3 && (
                      <span className="text-xs text-gray-500">
                        +{token.scopes.length - 3} more
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-3 px-4">
                  <TypeBadge type={token.token_type} />
                </td>
                <td className="py-3 px-4 text-gray-400">
                  {formatDate(token.created_at)}
                </td>
                <td className="py-3 px-4 text-gray-500">
                  {token.last_used_at ? formatDate(token.last_used_at) : "Never used"}
                </td>
                <td className="py-3 px-4">
                  <span className={expiry.className}>{expiry.label}</span>
                </td>
                <td className="py-3 px-4">
                  {!isRevoked && (
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => onEdit(token)}
                        className="p-1.5 text-gray-500 hover:text-gray-300 rounded-lg hover:bg-white/5 transition-colors"
                        title="Edit"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onRevoke(token)}
                        className="p-1.5 text-gray-500 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
                        title="Revoke"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                  {isRevoked && (
                    <span className="text-xs text-red-400/70">Revoked</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
