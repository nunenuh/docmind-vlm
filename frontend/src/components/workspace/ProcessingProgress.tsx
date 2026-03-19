import { useState, useCallback, useRef, useEffect } from "react";
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
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const startProcessing = useCallback(() => {
    setIsProcessing(true);
    setError(null);
    setShowDropdown(true);
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

  // Idle state — show the button
  if (!isProcessing && progress === 0 && !error) {
    return (
      <button
        onClick={startProcessing}
        className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-3 py-1.5 rounded transition-colors"
      >
        <Play className="w-3.5 h-3.5" />
        Process Document
      </button>
    );
  }

  // Active / completed / error — compact indicator + dropdown
  const activeStep = steps.find((s) => s.status === "active");
  const isDone = progress === 100 && !isProcessing;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Compact header indicator */}
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded transition-colors ${
          error
            ? "bg-red-600/20 text-red-400"
            : isDone
              ? "bg-green-600/20 text-green-400"
              : "bg-blue-600/20 text-blue-300"
        }`}
      >
        {isProcessing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
        {isDone && <CheckCircle className="w-3.5 h-3.5" />}
        {error && <AlertCircle className="w-3.5 h-3.5" />}
        {isProcessing && activeStep ? (
          <span className="capitalize">{activeStep.name}...</span>
        ) : isDone ? (
          "Done"
        ) : error ? (
          "Failed"
        ) : null}
      </button>

      {/* Dropdown with details */}
      {showDropdown && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50 p-3 space-y-3">
          {/* Progress bar */}
          <div className="w-full bg-gray-800 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full transition-all duration-300 ${
                error ? "bg-red-500" : "bg-blue-500"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Steps */}
          <div className="space-y-1.5">
            {steps.map((step) => (
              <div key={step.name} className="flex items-center gap-2">
                {step.status === "done" && <CheckCircle className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />}
                {step.status === "active" && <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin flex-shrink-0" />}
                {step.status === "pending" && <div className="w-3.5 h-3.5 rounded-full border border-gray-700 flex-shrink-0" />}
                {step.status === "error" && <AlertCircle className="w-3.5 h-3.5 text-red-400 flex-shrink-0" />}
                <span className={`text-xs capitalize ${step.status === "active" ? "text-white" : "text-gray-500"}`}>
                  {step.name}
                </span>
                {step.message && step.status === "active" && (
                  <span className="text-[10px] text-gray-600 ml-auto truncate max-w-[100px]">{step.message}</span>
                )}
              </div>
            ))}
          </div>

          {/* Error message */}
          {error && (
            <div className="text-xs text-red-400 bg-red-900/20 p-2 rounded">
              {error}
            </div>
          )}

          {/* Retry button on error */}
          {error && (
            <button
              onClick={startProcessing}
              className="w-full flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium py-2 rounded transition-colors"
            >
              <Play className="w-3 h-3" />
              Retry
            </button>
          )}

          {/* Process again after done */}
          {isDone && (
            <button
              onClick={startProcessing}
              className="w-full flex items-center justify-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium py-2 rounded transition-colors"
            >
              <Play className="w-3 h-3" />
              Reprocess
            </button>
          )}
        </div>
      )}
    </div>
  );
}
