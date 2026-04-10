import { AlertTriangle } from "lucide-react";
import type { TokenResponse } from "@/types/api-token";

interface RevokeTokenDialogProps {
  isOpen: boolean;
  token: TokenResponse | null;
  onClose: () => void;
  onConfirm: () => void;
}

export function RevokeTokenDialog({ isOpen, token, onClose, onConfirm }: RevokeTokenDialogProps) {
  if (!isOpen || !token) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-[#12121a] border border-[#1e1e2e] rounded-xl w-full max-w-md shadow-2xl mx-4">
        <div className="px-6 py-5 space-y-4">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Revoke API Key</h2>
              <p className="text-sm text-gray-400 mt-1">
                Are you sure you want to revoke{" "}
                <span className="text-white font-medium">{token.name}</span>?
              </p>
            </div>
          </div>

          <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-4 py-3 space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Name</span>
              <span className="text-sm text-white">{token.name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Prefix</span>
              <span className="text-sm text-gray-300 font-mono">{token.prefix}...</span>
            </div>
          </div>

          <div className="flex items-start gap-2 px-3 py-2.5 bg-red-500/5 border border-red-500/10 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-red-300/80">
              This action takes effect immediately. Any applications using this key will lose access.
            </p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-1">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white border border-[#1e1e2e] hover:border-gray-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors"
            >
              Revoke Key
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
