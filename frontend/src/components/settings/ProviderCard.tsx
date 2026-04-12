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

const ALL_PROVIDER_OPTIONS: { value: ProviderName; label: string; supportsEmbedding: boolean }[] = [
  { value: "dashscope", label: "DashScope (Qwen-VL)", supportsEmbedding: true },
  { value: "openai", label: "OpenAI (GPT-4o)", supportsEmbedding: true },
  { value: "openrouter", label: "OpenRouter (Multi-Provider)", supportsEmbedding: false },
  { value: "google", label: "Google (Gemini)", supportsEmbedding: true },
  { value: "ollama", label: "Ollama (Local)", supportsEmbedding: true },
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getProviderLabel(name: ProviderName): string {
  return ALL_PROVIDER_OPTIONS.find((o) => o.value === name)?.label ?? name;
}

function getProviderOptions(providerType: ProviderType) {
  if (providerType === "embedding") {
    return ALL_PROVIDER_OPTIONS.filter((o) => o.supportsEmbedding);
  }
  return ALL_PROVIDER_OPTIONS;
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

  const handleSave = () => {
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
          setIsEditing(false);
          resetForm();
        },
      },
    );
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
    </div>
  );
}
