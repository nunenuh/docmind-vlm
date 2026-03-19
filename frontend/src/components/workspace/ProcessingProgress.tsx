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

  return (
    <div className="p-4">
      {!isProcessing && progress === 0 && !error && (
        <button
          onClick={startProcessing}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-medium py-3 rounded-lg transition-colors"
        >
          <Play className="w-4 h-4" />
          Process Document
        </button>
      )}

      {(isProcessing || progress > 0) && (
        <div className="space-y-4">
          {/* Progress bar */}
          <div className="w-full bg-gray-800 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Steps */}
          <div className="space-y-2">
            {steps.map((step) => (
              <div key={step.name} className="flex items-center gap-3">
                {step.status === "done" && <CheckCircle className="w-4 h-4 text-green-400" />}
                {step.status === "active" && <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />}
                {step.status === "pending" && <div className="w-4 h-4 rounded-full border border-gray-700" />}
                {step.status === "error" && <AlertCircle className="w-4 h-4 text-red-400" />}
                <span className={`text-sm capitalize ${step.status === "active" ? "text-white" : "text-gray-500"}`}>
                  {step.name}
                </span>
                {step.message && step.status === "active" && (
                  <span className="text-xs text-gray-600 ml-auto">{step.message}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-900/20 border border-red-800 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-red-400">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        </div>
      )}

      {progress === 100 && !isProcessing && (
        <div className="mt-4 p-3 bg-green-900/20 border border-green-800 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-green-400">
            <CheckCircle className="w-4 h-4" />
            Processing complete
          </div>
        </div>
      )}
    </div>
  );
}
