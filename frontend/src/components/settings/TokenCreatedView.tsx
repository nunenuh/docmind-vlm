import { useState } from "react";
import { Copy, Check, AlertTriangle } from "lucide-react";
import type { TokenCreatedResponse } from "@/types/api-token";

interface TokenCreatedViewProps {
  token: TokenCreatedResponse;
  onClose: () => void;
}

export function TokenCreatedView({ token, onClose }: TokenCreatedViewProps) {
  const [copied, setCopied] = useState(false);
  const [curlCopied, setCurlCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(token.plain_token);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const curlSnippet = `curl -H "Authorization: Bearer ${token.plain_token}" \\
  ${window.location.origin}/api/v1/documents`;

  const handleCopyCurl = async () => {
    await navigator.clipboard.writeText(curlSnippet);
    setCurlCopied(true);
    setTimeout(() => setCurlCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div className="relative bg-[#12121a] border border-[#1e1e2e] rounded-xl w-full max-w-lg shadow-2xl mx-4">
        <div className="px-6 py-5 space-y-5">
          <div>
            <h2 className="text-lg font-semibold text-white">API Key Created</h2>
            <p className="text-sm text-gray-400 mt-1">
              Your new API key <span className="text-white font-medium">{token.name}</span> has been created.
            </p>
          </div>

          {/* Warning */}
          <div className="flex items-start gap-3 px-4 py-3 bg-amber-500/10 border border-amber-500/20 rounded-lg">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-300">
                Copy your key now
              </p>
              <p className="text-xs text-amber-400/80 mt-0.5">
                This is the only time the full key will be shown. Store it securely.
              </p>
            </div>
          </div>

          {/* Token display */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              API Key
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={token.plain_token}
                className="flex-1 bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white font-mono focus:outline-none"
              />
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border border-[#1e1e2e] hover:border-gray-700 rounded-lg transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4 text-emerald-400" />
                    <span className="text-emerald-400">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-400">Copy</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Quick start */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1.5">
              Quick Start
            </label>
            <div className="relative">
              <pre className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-4 py-3 text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap">
                {curlSnippet}
              </pre>
              <button
                onClick={handleCopyCurl}
                className="absolute top-2 right-2 p-1.5 text-gray-500 hover:text-gray-300 rounded transition-colors"
                title="Copy curl command"
              >
                {curlCopied ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
              </button>
            </div>
          </div>

          {/* Done */}
          <div className="flex justify-end pt-1">
            <button
              onClick={onClose}
              className="px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
