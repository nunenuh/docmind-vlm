import { useState } from "react";
import {
  Cpu,
  Zap,
  Eye,
  EyeOff,
  Check,
  X,
  Loader2,
  Trash2,
  Pencil,
  ChevronDown,
  Info,
} from "lucide-react";
import {
  useSetProvider,
  useDeleteProvider,
  useTestProvider,
} from "@/hooks/useProviderSettings";
import type {
  ProviderType,
  ProviderName,
  ProviderConfigResponse,
} from "@/types/provider";

interface ProviderCardProps {
  type: ProviderType;
  title: string;
  description: string;
  currentConfig: ProviderConfigResponse | null;
}

const VLM_PROVIDER_OPTIONS: { value: ProviderName; label: string }[] = [
  { value: "dashscope", label: "DashScope (Qwen-VL)" },
  { value: "openai", label: "OpenAI (GPT-4o)" },
  { value: "openrouter", label: "OpenRouter (Multi-Provider)" },
  { value: "google", label: "Google (Gemini)" },
  { value: "ollama", label: "Ollama (Local)" },
];

const EMBEDDING_PROVIDER_OPTIONS: { value: ProviderName; label: string }[] = [
  { value: "dashscope", label: "DashScope (Text Embedding)" },
  { value: "openai", label: "OpenAI (Embedding)" },
  { value: "openrouter", label: "OpenRouter (Multi-Provider)" },
  { value: "google", label: "Google (Embedding)" },
  { value: "ollama", label: "Ollama (Local)" },
];

const ALL_PROVIDER_OPTIONS = [...VLM_PROVIDER_OPTIONS, ...EMBEDDING_PROVIDER_OPTIONS];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getProviderOptions(providerType: ProviderType) {
  return providerType === "embedding" ? EMBEDDING_PROVIDER_OPTIONS : VLM_PROVIDER_OPTIONS;
}

function getProviderLabel(name: ProviderName, providerType?: ProviderType): string {
  const options = providerType ? getProviderOptions(providerType) : ALL_PROVIDER_OPTIONS;
  return options.find((o) => o.value === name)?.label ?? name;
}

export function ProviderCard({
  type,
  title,
  description,
  currentConfig,
}: ProviderCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [providerName, setProviderName] = useState<ProviderName>(
    currentConfig?.provider_name ?? "dashscope",
  );
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(
    currentConfig?.base_url ?? "http://localhost:11434",
  );
  const [showApiKey, setShowApiKey] = useState(false);
  const [modelName, setModelName] = useState(
    currentConfig?.model_name ?? "",
  );
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [testPassed, setTestPassed] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false);

  const setProviderMutation = useSetProvider();
  const deleteProviderMutation = useDeleteProvider();
  const testProviderMutation = useTestProvider();

  const isConfigured = currentConfig !== null && !isEditing;
  const showForm = !currentConfig || isEditing;

  const resetForm = () => {
    setProviderName(currentConfig?.provider_name ?? "dashscope");
    setApiKey("");
    setBaseUrl(currentConfig?.base_url ?? "http://localhost:11434");
    setModelName(currentConfig?.model_name ?? "");
    setAvailableModels([]);
    setTestPassed(false);
    setTestError(null);
    setShowApiKey(false);
  };

  const handleEdit = () => {
    resetForm();
    setIsEditing(true);
  };

  const handleCancel = () => {
    resetForm();
    setIsEditing(false);
  };

  const handleProviderChange = (name: ProviderName) => {
    setProviderName(name);
    setApiKey("");
    setBaseUrl(name === "ollama" ? "http://localhost:11434" : "");
    setModelName("");
    setAvailableModels([]);
    setTestPassed(false);
    setTestError(null);
  };

  const handleTest = () => {
    setTestError(null);
    setTestPassed(false);
    setAvailableModels([]);
    setModelName("");

    testProviderMutation.mutate(
      {
        provider_name: providerName,
        api_key: apiKey,
        base_url: providerName === "ollama" ? baseUrl : null,
        provider_type: type,
      },
      {
        onSuccess: (result) => {
          if (result.success) {
            setTestPassed(true);
            setAvailableModels(result.models);
            if (result.models.length === 1) {
              setModelName(result.models[0]);
            }
          } else {
            setTestError(result.error ?? "Connection test failed");
          }
        },
        onError: (error) => {
          setTestError(error.message);
        },
      },
    );
  };

  const [showEmbeddingWarning, setShowEmbeddingWarning] = useState(false);

  const doSave = () => {
    setProviderMutation.mutate(
      {
        type,
        data: {
          provider_name: providerName,
          api_key: apiKey,
          model_name: modelName,
          base_url: providerName === "ollama" ? baseUrl : null,
        },
      },
      {
        onSuccess: () => {
          setShowEmbeddingWarning(false);
          setIsEditing(false);
          resetForm();
        },
      },
    );
  };

  const handleSave = () => {
    if (type === "embedding" && currentConfig) {
      // Switching embedding model — warn about re-indexing
      const oldModel = currentConfig.model_name;
      const newModel = modelName;
      if (oldModel !== newModel || currentConfig.provider_name !== providerName) {
        setShowEmbeddingWarning(true);
        return;
      }
    }
    doSave();
  };

  const handleRemove = () => {
    deleteProviderMutation.mutate(type, {
      onSuccess: () => {
        setShowRemoveConfirm(false);
        resetForm();
        setIsEditing(false);
      },
    });
  };

  const TypeIcon = type === "vlm" ? Zap : Cpu;

  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6">
      {/* Header */}
      <div className="flex items-start gap-3 mb-4">
        <div className="p-2 rounded-lg bg-indigo-600/10">
          <TypeIcon className="w-5 h-5 text-indigo-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-semibold text-white">{title}</h3>
          <p className="text-sm text-gray-400 mt-0.5">{description}</p>
        </div>
      </div>

      {/* Configured status view */}
      {isConfigured && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 bg-[#0a0a0f] rounded-lg p-4 border border-[#1e1e2e]">
            <div>
              <p className="text-xs text-gray-500 mb-1">Provider</p>
              <p className="text-sm text-white font-medium">
                {getProviderLabel(currentConfig.provider_name)}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Model</p>
              <p className="text-sm text-white font-medium">
                {currentConfig.model_name}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">API Key</p>
              <p className="text-sm text-gray-300 font-mono">
                {currentConfig.api_key_prefix}{"****"}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-500 mb-1">Last Updated</p>
              <p className="text-sm text-gray-300">
                {formatDate(currentConfig.updated_at)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {currentConfig.is_validated && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                <Check className="w-3.5 h-3.5" />
                Validated
              </span>
            )}
            <div className="flex-1" />
            <button
              onClick={handleEdit}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
            >
              <Pencil className="w-3.5 h-3.5" />
              Edit
            </button>
            <button
              onClick={() => setShowRemoveConfirm(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Remove
            </button>
          </div>

          {/* Remove confirmation */}
          {showRemoveConfirm && (
            <div className="bg-red-500/5 border border-red-500/20 rounded-lg p-4">
              <p className="text-sm text-red-300 mb-3">
                Remove this provider? The system default will be used instead.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleRemove}
                  disabled={deleteProviderMutation.isPending}
                  className="px-3 py-1.5 text-sm bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors disabled:opacity-50"
                >
                  {deleteProviderMutation.isPending ? "Removing..." : "Confirm Remove"}
                </button>
                <button
                  onClick={() => setShowRemoveConfirm(false)}
                  className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Form view */}
      {showForm && (
        <div className="space-y-4">
          {/* Provider select */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Provider
            </label>
            <div className="relative">
              <select
                value={providerName}
                onChange={(e) =>
                  handleProviderChange(e.target.value as ProviderName)
                }
                className="w-full appearance-none bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 pr-10"
              >
                {getProviderOptions(type).map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>
          </div>

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              API Key
            </label>
            <div className="relative">
              <input
                type={showApiKey ? "text" : "password"}
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setTestPassed(false);
                  setAvailableModels([]);
                  setModelName("");
                  setTestError(null);
                }}
                placeholder={
                  providerName === "ollama"
                    ? "Optional for local Ollama"
                    : "Enter your API key"
                }
                className="w-full bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showApiKey ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          {/* Base URL (Ollama only) */}
          {providerName === "ollama" && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Base URL
              </label>
              <input
                type="text"
                value={baseUrl}
                onChange={(e) => {
                  setBaseUrl(e.target.value);
                  setTestPassed(false);
                  setAvailableModels([]);
                  setModelName("");
                  setTestError(null);
                }}
                placeholder="http://localhost:11434"
                className="w-full bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
              />
            </div>
          )}

          {/* Test Connection */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleTest}
              disabled={
                testProviderMutation.isPending ||
                (!apiKey && providerName !== "ollama")
              }
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-[#0a0a0f] border border-[#1e1e2e] text-white rounded-lg hover:border-indigo-500/50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {testProviderMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Testing...
                </>
              ) : (
                "Test Connection"
              )}
            </button>

            {testPassed && (
              <span className="flex items-center gap-1.5 text-sm text-emerald-400">
                <Check className="w-4 h-4" />
                Connected
              </span>
            )}
            {testError && (
              <span className="flex items-center gap-1.5 text-sm text-red-400 min-w-0">
                <X className="w-4 h-4 flex-shrink-0" />
                <span className="truncate">{testError}</span>
              </span>
            )}
          </div>

          {/* Model select */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Model
            </label>
            <div className="relative">
              <select
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                disabled={!testPassed || availableModels.length === 0}
                className="w-full appearance-none bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500 pr-10 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <option value="">Select a model...</option>
                {availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            </div>
            {!testPassed && (
              <p className="text-xs text-gray-500 mt-1.5 flex items-center gap-1">
                <Info className="w-3 h-3" />
                Test connection first to see available models
              </p>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSave}
              disabled={
                !testPassed ||
                !modelName ||
                setProviderMutation.isPending
              }
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors shadow-lg shadow-indigo-500/20 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
            >
              {setProviderMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Saving...
                </>
              ) : (
                "Save Provider"
              )}
            </button>
            {currentConfig && (
              <button
                onClick={handleCancel}
                className="px-4 py-2.5 text-sm text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}

      {/* Embedding model change warning dialog */}
      {showEmbeddingWarning && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowEmbeddingWarning(false)}
          />
          <div className="relative bg-[#12121a] border border-amber-500/30 rounded-xl w-full max-w-lg mx-4 shadow-2xl">
            <div className="px-6 py-5 space-y-4">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-amber-500/10 rounded-lg shrink-0 mt-0.5">
                  <Info className="w-5 h-5 text-amber-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">
                    Embedding Model Change
                  </h3>
                  <p className="text-sm text-gray-400 mt-1">
                    Changing the embedding model requires all documents to be
                    re-indexed. Existing vectors are incompatible with the new model.
                  </p>
                </div>
              </div>

              <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Current model</span>
                  <span className="text-gray-300 font-mono text-xs">
                    {currentConfig
                      ? `${currentConfig.provider_name}/${currentConfig.model_name}`
                      : "System default"}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">New model</span>
                  <span className="text-white font-mono text-xs">
                    {providerName}/{modelName}
                  </span>
                </div>
              </div>

              <div className="bg-amber-500/5 border border-amber-500/10 rounded-lg px-4 py-3">
                <p className="text-xs text-gray-400 leading-relaxed">
                  <span className="text-amber-400 font-medium">What happens: </span>
                  All project documents will need to be re-indexed with the new embedding
                  model. Until re-indexing is complete, RAG search results may be
                  inaccurate or unavailable. You can trigger re-indexing from each
                  project's settings.
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-1">
                <button
                  onClick={() => setShowEmbeddingWarning(false)}
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={doSave}
                  disabled={setProviderMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg transition-colors"
                >
                  {setProviderMutation.isPending && (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  )}
                  Change Model & Save
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
