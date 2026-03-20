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
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium px-4 py-2 rounded-md transition-all duration-200 shadow-sm shadow-blue-600/20 hover:shadow-blue-500/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 focus-visible:ring-offset-gray-900"
      >
        <Play className="w-4 h-4" />
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
        className={`flex items-center gap-2 text-xs font-medium px-3 py-2 rounded-md transition-all duration-200 border focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${
          error
            ? "bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/15"
            : isDone
              ? "bg-green-500/10 text-green-400 border-green-500/20 hover:bg-green-500/15"
              : "bg-blue-500/10 text-blue-300 border-blue-500/20 hover:bg-blue-500/15"
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
        {isProcessing && (
          <span className="text-[10px] tabular-nums opacity-70">{Math.round(progress)}%</span>
        )}
      </button>

      {/* Dropdown with details */}
      {showDropdown && (
        <div className="absolute right-0 top-full mt-2 w-72 bg-gray-900 border border-gray-800 rounded-lg shadow-2xl shadow-black/50 z-50 overflow-hidden">
          {/* Progress bar at top */}
          <div className="w-full bg-gray-800 h-1">
            <div
              className={`h-1 transition-all duration-500 ease-out ${
                error ? "bg-red-500" : isDone ? "bg-green-500" : "bg-blue-500"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="p-4 space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-300">Pipeline Progress</span>
              <span className="text-xs text-gray-500 tabular-nums">{Math.round(progress)}%</span>
            </div>

            {/* Steps */}
            <div className="space-y-2">
              {steps.map((step, idx) => (
                <div key={step.name} className="flex items-center gap-2.5">
                  {step.status === "done" && (
                    <div className="w-5 h-5 rounded-full bg-green-500/15 flex items-center justify-center flex-shrink-0">
                      <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                    </div>
                  )}
                  {step.status === "active" && (
                    <div className="w-5 h-5 rounded-full bg-blue-500/15 flex items-center justify-center flex-shrink-0">
                      <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin" />
                    </div>
                  )}
                  {step.status === "pending" && (
                    <div className="w-5 h-5 rounded-full border border-gray-700 flex items-center justify-center flex-shrink-0">
                      <span className="text-[9px] text-gray-600 font-medium">{idx + 1}</span>
                    </div>
                  )}
                  {step.status === "error" && (
                    <div className="w-5 h-5 rounded-full bg-red-500/15 flex items-center justify-center flex-shrink-0">
                      <AlertCircle className="w-3.5 h-3.5 text-red-400" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <span className={`text-xs capitalize ${
                      step.status === "active" ? "text-white font-medium" :
                      step.status === "done" ? "text-gray-400" : "text-gray-600"
                    }`}>
                      {step.name}
                    </span>
                  </div>
                  {step.message && step.status === "active" && (
                    <span className="text-[10px] text-gray-500 truncate max-w-[100px]">{step.message}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Error message */}
            {error && (
              <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 p-2.5 rounded-md">
                {error}
              </div>
            )}

            {/* Retry button on error */}
            {error && (
              <button
                onClick={startProcessing}
                className="w-full flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium py-2 rounded-md transition-all duration-200"
              >
                <Play className="w-3 h-3" />
                Retry
              </button>
            )}

            {/* Process again after done */}
            {isDone && (
              <button
                onClick={startProcessing}
                className="w-full flex items-center justify-center gap-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-medium py-2 rounded-md border border-gray-700 transition-all duration-200"
              >
                <Play className="w-3 h-3" />
                Reprocess
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
