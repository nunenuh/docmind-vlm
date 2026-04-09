import { useState, useCallback } from "react";
import { Loader2, CheckCircle, AlertCircle, Play } from "lucide-react";
import { processDocument } from "@/lib/api";
import { useWorkspaceStore } from "@/stores/workspace-store";

interface ProcessingProgressProps {
  documentId: string;
  templateType?: string | null;
  onComplete?: () => void;
}

interface StepStatus {
  name: string;
  status: "pending" | "active" | "done" | "error";
  message?: string;
}

const PIPELINE_STEPS = ["preprocess", "extract", "postprocess", "store"];

export function ProcessingProgress({ documentId, templateType, onComplete }: ProcessingProgressProps) {
  const { isProcessing, setIsProcessing } = useWorkspaceStore();
  const [steps, setSteps] = useState<StepStatus[]>(
    PIPELINE_STEPS.map((name) => ({ name, status: "pending" })),
  );
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const startProcessing = useCallback(() => {
    setIsProcessing(true);
    setError(null);
    setSteps(PIPELINE_STEPS.map((name) => ({ name, status: "pending" })));
    setProgress(0);

    processDocument(
      documentId,
      templateType ?? undefined,
      (data: unknown) => {
        const event = data as Record<string, unknown>;
        const step = event.step as string;
        const pct = event.progress as number;

        if (step === "error") {
          setError((event.message as string) ?? "Processing failed");
          setIsProcessing(false);
          return;
        }

        if (step === "complete") {
          setProgress(100);
          setSteps((prev) => prev.map((s) => ({ ...s, status: "done" })));
          setIsProcessing(false);
          onComplete?.();
          return;
        }

        if (step && pct != null) {
          setProgress(Math.max(0, Math.min(100, pct)));
          setSteps((prev) =>
            prev.map((s) => {
              if (s.name === step) return { ...s, status: "active", message: event.message as string };
              if (PIPELINE_STEPS.indexOf(s.name) < PIPELINE_STEPS.indexOf(step)) return { ...s, status: "done" };
              return s;
            }),
          );
        }
      },
      (err: Error) => {
        setError(err.message);
        setIsProcessing(false);
      },
      () => {
        setIsProcessing(false);
      },
    );
  }, [documentId, templateType, setIsProcessing, onComplete]);

  const isDone = progress === 100 && !isProcessing;

  // Idle state
  if (!isProcessing && progress === 0 && !error) {
    return (
      <button
        onClick={startProcessing}
        className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2.5 rounded-lg transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
      >
        <Play className="w-4 h-4" />
        Process Document
      </button>
    );
  }

  // Active / completed / error - inline progress
  return (
    <div className="space-y-3">
      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-[#1a1a25] rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ease-out rounded-full ${
              error ? "bg-rose-500" : isDone ? "bg-emerald-500" : "bg-indigo-500"
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 tabular-nums w-8 text-right">
          {Math.round(progress)}%
        </span>
      </div>

      {/* Steps inline */}
      <div className="flex items-center gap-1">
        {steps.map((step, idx) => (
          <div key={step.name} className="flex items-center gap-1">
            {idx > 0 && <div className="w-3 h-px bg-[#2a2a3a]" />}
            <div className="flex items-center gap-1.5">
              {step.status === "done" && <CheckCircle className="w-3 h-3 text-emerald-400" />}
              {step.status === "active" && <Loader2 className="w-3 h-3 text-indigo-400 animate-spin" />}
              {step.status === "pending" && (
                <div className="w-3 h-3 rounded-full border border-[#2a2a3a]" />
              )}
              {step.status === "error" && <AlertCircle className="w-3 h-3 text-rose-400" />}
              <span
                className={`text-xs capitalize ${
                  step.status === "active"
                    ? "text-white font-medium"
                    : step.status === "done"
                      ? "text-gray-500"
                      : "text-gray-600"
                }`}
              >
                {step.name}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Error message */}
      {error && (
        <div className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg">
          {error}
        </div>
      )}

      {/* Action buttons */}
      {(error || isDone) && (
        <button
          onClick={startProcessing}
          className={`w-full flex items-center justify-center gap-1.5 text-xs font-medium py-2 rounded-lg transition-colors ${
            error
              ? "bg-indigo-600 hover:bg-indigo-700 text-white"
              : "bg-white/5 hover:bg-white/10 text-gray-300 border border-[#2a2a3a]"
          }`}
        >
          <Play className="w-3 h-3" />
          {error ? "Retry" : "Reprocess"}
        </button>
      )}
    </div>
  );
}
