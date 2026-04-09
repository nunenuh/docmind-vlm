# Issue #31: ComparePanel + ProcessingProgress

## Summary

Implement the ComparePanel (side-by-side display of raw VLM extraction vs enhanced pipeline extraction with color-coded diffs) and ProcessingProgress (SSE-powered step-by-step progress visualization during document processing). ComparePanel uses the `useComparison` hook. ProcessingProgress subscribes to the `processDocument` SSE stream and displays pipeline steps with status icons and an overall progress bar. These are the final two workspace tab/overlay components.

## Context

- **Phase**: 6 — Frontend
- **Priority**: P1
- **Labels**: `phase-6-frontend`, `frontend`, `tdd`
- **Dependencies**: #28 (Workspace layout), #29 (ExtractionPanel for comparison context)
- **Branch**: `feat/31-compare-progress`
- **Estimated scope**: M

## Specs to Read

- `specs/frontend/components.md` — ComparePanel full implementation, ProcessingProgress full implementation
- `specs/frontend/state.md` — useComparison hook, isProcessing in workspace-store, query invalidation after processing
- `specs/frontend/api-client.md` — fetchComparison, processDocument SSE stream, ComparisonResponse type
- `docs/blueprint/02-product/user-interface-specification.md` — Sections 2.8 (Compare Tab)
- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 3.1-3.4, AC 8.1-8.4

## Current State (Scaffold)

**File: `frontend/src/components/workspace/ComparePanel.tsx`**
```typescript
export function ComparePanel() {
  return <div>ComparePanel</div>;
}
```

**File: `frontend/src/components/workspace/ProcessingProgress.tsx`**
```typescript
export function ProcessingProgress() {
  return <div>ProcessingProgress</div>;
}
```

**Hook already implemented:**
```typescript
// frontend/src/hooks/useExtraction.ts
export function useComparison(documentId: string) {
  return useQuery({ queryKey: ["comparison", documentId], queryFn: () => fetchComparison(documentId), enabled: !!documentId });
}
```

**API already implemented:**
```typescript
// frontend/src/lib/api.ts
export function processDocument(
  id: string, templateType: string | undefined,
  onMessage: (data: unknown) => void, onError: (error: Error) => void, onComplete: () => void,
): AbortController { ... }
```

**Types:**
```typescript
// frontend/src/types/api.ts
export interface ComparisonResponse {
  enhanced_fields: ExtractedFieldResponse[];
  raw_fields: Record<string, unknown>[];
  corrected: string[];    // field IDs corrected by pipeline
  added: string[];        // field IDs added by pipeline
}
```

## Requirements

### Functional

1. **ComparePanel**:
   - Side-by-side two-column layout: "Raw Extraction" (left) vs "Post-Processed" (right)
   - Each field row color-coded by diff status:
     - Blue left border: field was corrected by post-processing
     - Green left border: field was added by post-processing
     - Red left border: field was removed by post-processing
     - No border: unchanged
   - Legend badges at top: Corrected (blue), Added (green), Removed (red)
   - Each field shows name, value, and confidence badge
   - Summary stats: "X corrected, Y added, Z unchanged"
   - Empty state: "Process a document to compare extraction results."
2. **ProcessingProgress**:
   - Vertical step list with 4 predefined steps: "Analyzing image quality", "Preprocessing document", "Extracting content", "Post-processing fields"
   - Each step shows status icon: pending (gray circle), active (spinning loader), complete (green checkmark), error (red circle)
   - Overall progress bar (0-100%)
   - Progress percentage badge
   - SSE stream events update step states and progress
   - On final step complete: call `onComplete()` callback
   - Error state: show error message, allow retry
   - Cleanup: close EventSource on unmount

### Non-Functional

- ProcessingProgress visible as overlay on workspace during processing
- Comparison loads from pre-computed data in < 1 second — AC 8.4
- Processing shows step-by-step progress — AC 3.1
- Processing failure shows clear error with failed step — AC 3.4

## Implementation Plan

### ComparePanel

**`frontend/src/components/workspace/ComparePanel.tsx`**:
```typescript
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBadge } from "@/components/workspace/ConfidenceBadge";
import type { ComparisonResponse, ExtractedFieldResponse } from "@/types/api";

interface ComparePanelProps {
  comparison: ComparisonResponse | null;
}

function getDiffStatus(fieldId: string, comparison: ComparisonResponse): "corrected" | "added" | "removed" | "unchanged" {
  if (comparison.corrected.includes(fieldId)) return "corrected";
  if (comparison.added.includes(fieldId)) return "added";
  return "unchanged";
}

const DIFF_COLORS = {
  corrected: "bg-blue-50 dark:bg-blue-950 border-l-2 border-l-blue-500",
  added: "bg-green-50 dark:bg-green-950 border-l-2 border-l-green-500",
  removed: "bg-red-50 dark:bg-red-950 border-l-2 border-l-red-500",
  unchanged: "",
} as const;

export function ComparePanel({ comparison }: ComparePanelProps) {
  if (!comparison) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Process a document to compare extraction results.
      </div>
    );
  }

  const correctedCount = comparison.corrected.length;
  const addedCount = comparison.added.length;
  const unchangedCount = comparison.enhanced_fields.length - correctedCount - addedCount;

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Extraction Comparison</h3>
        <div className="flex gap-2 text-xs">
          <Badge variant="outline" className="border-blue-500 text-blue-700">Corrected ({correctedCount})</Badge>
          <Badge variant="outline" className="border-green-500 text-green-700">Added ({addedCount})</Badge>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {correctedCount} corrected, {addedCount} added, {unchangedCount} unchanged
      </p>

      <ScrollArea className="flex-1">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Raw Extraction</p>
            <div className="flex flex-col gap-1">
              {comparison.raw_fields.map((field, idx) => (
                <div key={idx} className="rounded px-2 py-1.5 text-sm">
                  <span className="font-medium">{String(field.field_key ?? "—")}:</span>{" "}
                  <span className="text-muted-foreground">{String(field.field_value ?? "—")}</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Post-Processed</p>
            <div className="flex flex-col gap-1">
              {comparison.enhanced_fields.map((field) => {
                const status = getDiffStatus(field.id, comparison);
                return (
                  <div key={field.id} className={`rounded px-2 py-1.5 text-sm ${DIFF_COLORS[status]}`}>
                    <span className="font-medium">{field.field_key ?? "—"}:</span>{" "}
                    <span className="text-muted-foreground">{field.field_value ?? "—"}</span>
                    <ConfidenceBadge confidence={field.confidence} showValue />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
```

### ProcessingProgress

**`frontend/src/components/workspace/ProcessingProgress.tsx`**:
```typescript
import { useState, useEffect, useRef } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Loader2, Circle, AlertCircle } from "lucide-react";
import { processDocument } from "@/lib/api";

interface ProcessingProgressProps {
  documentId: string;
  templateType?: string;
  onComplete: () => void;
}

interface ProcessingStep {
  name: string;
  status: "pending" | "active" | "complete" | "error";
  message?: string;
}

const INITIAL_STEPS: ProcessingStep[] = [
  { name: "Analyzing image quality", status: "pending" },
  { name: "Preprocessing document", status: "pending" },
  { name: "Extracting content", status: "pending" },
  { name: "Post-processing fields", status: "pending" },
];

function stepIcon(status: ProcessingStep["status"]) {
  switch (status) {
    case "complete": return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "active": return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
    case "error": return <AlertCircle className="h-4 w-4 text-destructive" />;
    default: return <Circle className="h-4 w-4 text-muted-foreground" />;
  }
}

export function ProcessingProgress({ documentId, templateType, onComplete }: ProcessingProgressProps) {
  const [steps, setSteps] = useState<ProcessingStep[]>(INITIAL_STEPS);
  const [overallProgress, setOverallProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const controller = processDocument(
      documentId,
      templateType,
      (event) => {
        const data = event as {
          step: number;
          name: string;
          status: string;
          progress: number;
          message?: string;
        };

        setSteps((prev) =>
          prev.map((s, idx) => {
            if (idx < data.step) return { ...s, status: "complete" };
            if (idx === data.step) return { ...s, status: data.status as ProcessingStep["status"], message: data.message };
            return s;
          }),
        );
        setOverallProgress(data.progress);

        if (data.status === "complete" && data.step === INITIAL_STEPS.length - 1) {
          onComplete();
        }
      },
      (err) => {
        setError(err.message ?? "Processing failed. Please try again.");
      },
      () => { /* stream ended */ },
    );

    controllerRef.current = controller;

    return () => { controller.abort(); };
  }, [documentId, templateType, onComplete]);

  return (
    <div className="flex flex-col gap-4 p-4 rounded-lg border bg-card">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Processing Document</h3>
        <Badge variant="secondary">{overallProgress}%</Badge>
      </div>
      <Progress value={overallProgress} />
      <div className="flex flex-col gap-2">
        {steps.map((step, idx) => (
          <div key={idx} className="flex items-center gap-2 text-sm">
            {stepIcon(step.status)}
            <span className={step.status === "active" ? "font-medium" : "text-muted-foreground"}>
              {step.name}
            </span>
            {step.message && (
              <span className="text-xs text-muted-foreground ml-auto">{step.message}</span>
            )}
          </div>
        ))}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
```

### Integration in Workspace.tsx

```typescript
// In Workspace.tsx:
const { isProcessing, setIsProcessing } = useWorkspaceStore();
const queryClient = useQueryClient();

const handleProcess = () => {
  setIsProcessing(true);
};

const handleProcessingComplete = () => {
  setIsProcessing(false);
  // Invalidate all extraction-related queries
  queryClient.invalidateQueries({ queryKey: ["extraction", documentId] });
  queryClient.invalidateQueries({ queryKey: ["audit-trail", documentId] });
  queryClient.invalidateQueries({ queryKey: ["overlay", documentId] });
  queryClient.invalidateQueries({ queryKey: ["comparison", documentId] });
};

// Render ProcessingProgress as overlay when isProcessing is true
{isProcessing && (
  <div className="absolute inset-0 bg-background/80 flex items-center justify-center z-20">
    <ProcessingProgress documentId={documentId} onComplete={handleProcessingComplete} />
  </div>
)}
```

### SSE Event Format for Processing

```json
{"step": 0, "name": "Analyzing image quality", "status": "active", "progress": 10}
{"step": 0, "name": "Analyzing image quality", "status": "complete", "progress": 25}
{"step": 1, "name": "Preprocessing document", "status": "active", "progress": 30, "message": "Deskewing 4.2 degrees"}
{"step": 1, "name": "Preprocessing document", "status": "complete", "progress": 50}
{"step": 2, "name": "Extracting content", "status": "active", "progress": 55}
{"step": 2, "name": "Extracting content", "status": "complete", "progress": 80}
{"step": 3, "name": "Post-processing fields", "status": "active", "progress": 85}
{"step": 3, "name": "Post-processing fields", "status": "complete", "progress": 100}
```

### shadcn/ui Components Needed

```bash
cd frontend
npx shadcn@latest add progress badge scroll-area
```

## Acceptance Criteria

- [ ] Processing shows step-by-step progress: quality -> preprocess -> extract -> post-process — AC 3.1
- [ ] Processing failure shows clear error message with failed step — AC 3.4
- [ ] Progress bar updates in real-time from SSE events
- [ ] Step icons update: pending -> active (spinner) -> complete (checkmark)
- [ ] On processing complete, extraction queries are invalidated
- [ ] ComparePanel shows side-by-side raw vs enhanced — AC 8.1
- [ ] Corrected fields highlighted in blue — AC 8.2
- [ ] Added fields highlighted in green — AC 8.3
- [ ] Comparison loads in < 1 second — AC 8.4
- [ ] Summary stats shown (corrected, added, unchanged counts)
- [ ] Empty state for ComparePanel when no comparison data
- [ ] All components have TypeScript props interfaces
- [ ] SSE stream cleaned up on unmount (abort controller)

## Files Changed

- `frontend/src/components/workspace/ComparePanel.tsx` — implement from stub
- `frontend/src/components/workspace/ProcessingProgress.tsx` — implement from stub
- `frontend/src/pages/Workspace.tsx` — wire ComparePanel to "compare" tab, add ProcessingProgress overlay

## Verification

```bash
cd frontend
npm run typecheck
npm run lint
npm run dev
# Manual testing (requires running backend):
# 1. Open workspace with uploaded (unprocessed) document → click "Process"
# 2. ProcessingProgress overlay appears with step list
# 3. Steps animate: pending → active (spinner) → complete (checkmark)
# 4. Progress bar fills from 0% to 100%
# 5. On complete: overlay disappears, extraction data loads
# 6. Switch to Compare tab → side-by-side view with diff colors
# 7. Corrected fields have blue border, added have green
# 8. Summary stats match actual diff counts
```
