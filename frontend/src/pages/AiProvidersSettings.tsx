import { Loader2, AlertCircle, Info } from "lucide-react";
import { useProviders } from "@/hooks/useProviderSettings";
import { ProviderCard } from "@/components/settings/ProviderCard";

export function AiProvidersSettings() {
  const { data, isLoading, isError, error } = useProviders();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-white">AI Providers</h2>
        <p className="text-sm text-gray-400 mt-1">
          Configure your own API keys for VLM and embedding providers
        </p>
      </div>

      {/* Info box */}
      <div className="flex items-start gap-3 bg-indigo-600/5 border border-indigo-500/20 rounded-xl px-4 py-3">
        <Info className="w-4 h-4 text-indigo-400 mt-0.5 flex-shrink-0" />
        <p className="text-sm text-indigo-300/80">
          Not configured? The system default provider will be used
          automatically.
        </p>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading providers...</p>
        </div>
      ) : isError ? (
        <div className="flex flex-col items-center justify-center py-20">
          <AlertCircle className="w-8 h-8 text-red-400 mb-3" />
          <p className="text-sm text-red-400">
            Failed to load providers:{" "}
            {(error as Error)?.message ?? "Unknown error"}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <ProviderCard
            type="vlm"
            title="Chat & Extraction (VLM)"
            description="Vision Language Model for document extraction and chat"
            currentConfig={data?.vlm ?? null}
          />
          <ProviderCard
            type="embedding"
            title="Embedding (RAG)"
            description="Embedding model for knowledge base search"
            currentConfig={data?.embedding ?? null}
          />
        </div>
      )}
    </div>
  );
}
