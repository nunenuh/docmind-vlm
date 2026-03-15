# Issue #29: ExtractionPanel + AuditPanel + ConfidenceBadge

## Summary

Implement the ExtractionPanel (field list table with confidence badges, JSON toggle view, field selection highlighting synced with DocumentViewer), the AuditPanel (timeline of pipeline processing steps with durations), and the reusable ConfidenceBadge component. ExtractionPanel uses `useExtraction` hook data. AuditPanel uses `useAuditTrail` hook. Field selection in ExtractionPanel triggers `selectField` in workspace-store, which highlights the corresponding bounding box in the DocumentViewer.

## Context

- **Phase**: 6 — Frontend
- **Priority**: P0
- **Labels**: `phase-6-frontend`, `frontend`, `tdd`
- **Dependencies**: #28 (Workspace layout renders these panels in tabs)
- **Branch**: `feat/29-extraction-panel`
- **Estimated scope**: M

## Specs to Read

- `specs/frontend/components.md` — ExtractionPanel full implementation, ConfidenceBadge component
- `specs/frontend/state.md` — useExtraction, useAuditTrail hooks, selectedFieldId in workspace-store
- `specs/frontend/api-client.md` — ExtractionResponse, AuditEntryResponse, ExtractedFieldResponse types
- `docs/blueprint/02-product/user-interface-specification.md` — Sections 2.5 (Extraction Tab), 2.7 (Audit Tab)
- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 4.1-4.4, AC 6.1-6.3

## Current State (Scaffold)

**File: `frontend/src/components/workspace/ExtractionPanel.tsx`**
```typescript
export function ExtractionPanel() {
  return <div>ExtractionPanel</div>;
}
```

**File: `frontend/src/components/workspace/ConfidenceBadge.tsx`**
```typescript
export function ConfidenceBadge() {
  return <div>ConfidenceBadge</div>;
}
```

**Missing files:**
- `frontend/src/components/workspace/AuditPanel.tsx` — needs to be created

**Hooks already implemented:**
```typescript
// frontend/src/hooks/useExtraction.ts
export function useExtraction(documentId: string) {
  return useQuery({ queryKey: ["extraction", documentId], queryFn: () => fetchExtraction(documentId), enabled: !!documentId });
}

export function useAuditTrail(documentId: string) {
  return useQuery({ queryKey: ["audit-trail", documentId], queryFn: () => fetchAuditTrail(documentId), enabled: !!documentId });
}
```

## Requirements

### Functional

1. **ConfidenceBadge**: Reusable badge component. Props: `confidence` (0.0-1.0), `showValue` (boolean). Colors: green (>= 0.8 "High"), yellow (>= 0.5 "Medium"), red (< 0.5 "Low"). When `showValue=true`, shows percentage.
2. **ExtractionPanel**:
   - Header: "Extracted Fields" title with field count badge
   - View toggle: Table / JSON tabs
   - Table view: columns = Field Name, Value (truncated), Confidence (ConfidenceBadge with showValue)
   - Clicking a row calls `onFieldSelect(fieldId)` which updates workspace-store.selectedFieldId
   - Selected row highlighted with primary/10 background
   - JSON view: formatted JSON output in a `<pre>` block with monospace font
   - Empty state: "Process a document to see extracted fields."
3. **AuditPanel**:
   - Vertical timeline of processing steps
   - Each step shows: step name, duration (ms), status icon (complete/active/pending)
   - Steps ordered by `step_order`
   - Input/output summaries expandable on click
   - Empty state: "Process a document to see the audit trail."

### Non-Functional

- ExtractionPanel scrollable for long field lists (ScrollArea)
- Table rows use hover state for discoverability
- JSON view uses word-wrap for long values
- ConfidenceBadge supports dark mode colors

## Implementation Plan

### ConfidenceBadge

**`frontend/src/components/workspace/ConfidenceBadge.tsx`**:
```typescript
import { Badge } from "@/components/ui/badge";

interface ConfidenceBadgeProps {
  confidence: number;
  showValue?: boolean;
}

const THRESHOLDS = {
  high: { min: 0.8, color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200", label: "High" },
  medium: { min: 0.5, color: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200", label: "Medium" },
  low: { min: 0, color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200", label: "Low" },
} as const;

function getThreshold(confidence: number) {
  if (confidence >= THRESHOLDS.high.min) return THRESHOLDS.high;
  if (confidence >= THRESHOLDS.medium.min) return THRESHOLDS.medium;
  return THRESHOLDS.low;
}

export function ConfidenceBadge({ confidence, showValue = false }: ConfidenceBadgeProps) {
  const threshold = getThreshold(confidence);
  return (
    <Badge variant="secondary" className={`${threshold.color} text-xs`}>
      {showValue ? `${(confidence * 100).toFixed(0)}%` : threshold.label}
    </Badge>
  );
}
```

### ExtractionPanel

**`frontend/src/components/workspace/ExtractionPanel.tsx`**:
```typescript
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfidenceBadge } from "@/components/workspace/ConfidenceBadge";
import type { ExtractionResponse } from "@/types/api";

interface ExtractionPanelProps {
  extraction: ExtractionResponse | null;
  onFieldSelect: (fieldId: string) => void;
  selectedFieldId: string | null;
}

export function ExtractionPanel({ extraction, onFieldSelect, selectedFieldId }: ExtractionPanelProps) {
  const [viewMode, setViewMode] = useState<"table" | "json">("table");

  if (!extraction) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Process a document to see extracted fields.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold">Extracted Fields</h3>
          <Badge variant="secondary">{extraction.fields.length}</Badge>
        </div>
        <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as "table" | "json")}>
          <TabsList className="h-7">
            <TabsTrigger value="table" className="text-xs px-2 h-6">Table</TabsTrigger>
            <TabsTrigger value="json" className="text-xs px-2 h-6">JSON</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {viewMode === "table" && (
        <ScrollArea className="flex-1">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs text-muted-foreground">
                <th className="pb-2 pr-3">Field</th>
                <th className="pb-2 pr-3">Value</th>
                <th className="pb-2">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {extraction.fields.map((field) => (
                <tr
                  key={field.id}
                  onClick={() => onFieldSelect(field.id)}
                  className={`border-b cursor-pointer transition-colors hover:bg-muted/50 ${
                    field.id === selectedFieldId ? "bg-primary/10" : ""
                  }`}
                >
                  <td className="py-2 pr-3 font-medium">{field.field_key ?? field.field_type}</td>
                  <td className="py-2 pr-3 text-muted-foreground truncate max-w-[200px]">{field.field_value ?? "—"}</td>
                  <td className="py-2"><ConfidenceBadge confidence={field.confidence} showValue /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      )}

      {viewMode === "json" && (
        <ScrollArea className="flex-1">
          <pre className="text-xs bg-muted rounded p-3 overflow-x-auto whitespace-pre-wrap font-mono">
            {JSON.stringify(extraction, null, 2)}
          </pre>
        </ScrollArea>
      )}
    </div>
  );
}
```

### AuditPanel

**`frontend/src/components/workspace/AuditPanel.tsx`** (new file):
```typescript
import { ScrollArea } from "@/components/ui/scroll-area";
import { CheckCircle2, Clock, Circle } from "lucide-react";
import type { AuditEntryResponse } from "@/types/api";

interface AuditPanelProps {
  auditTrail: AuditEntryResponse[] | null;
}

export function AuditPanel({ auditTrail }: AuditPanelProps) {
  if (!auditTrail || auditTrail.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        Process a document to see the audit trail.
      </div>
    );
  }

  const sorted = [...auditTrail].sort((a, b) => a.step_order - b.step_order);

  return (
    <ScrollArea className="h-full">
      <div className="flex flex-col gap-1 p-1">
        {sorted.map((entry) => (
          <div key={entry.step_name} className="flex items-start gap-3 p-2 rounded hover:bg-muted/50">
            <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium">{entry.step_name}</p>
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {entry.duration_ms}ms
              </p>
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
```

### Data Flow

```
Workspace.tsx
  → useExtraction(documentId) → extraction data
  → useAuditTrail(documentId) → audit trail data
  → Passes to ExtractionPanel as props
  → Passes to AuditPanel as props
  → ExtractionPanel.onFieldSelect → workspace-store.selectField(fieldId)
  → DocumentViewer reads selectedFieldId → highlights bounding box
  → DocumentViewer.onFieldClick → workspace-store.selectField(fieldId)
  → ExtractionPanel reads selectedFieldId → highlights table row
```

### shadcn/ui Components Needed

```bash
cd frontend
npx shadcn@latest add badge tabs scroll-area
```

## Acceptance Criteria

- [ ] ExtractionPanel shows field list in table format — AC 4.2, AC 4.4
- [ ] Each field shows confidence score badge (green/yellow/red) — AC 6.2
- [ ] Clicking a field row highlights it and syncs with DocumentViewer — AC 6.1
- [ ] JSON view toggle shows formatted extraction JSON — AC 4.4
- [ ] Field count badge shows total fields
- [ ] Empty state shown when no extraction data
- [ ] ConfidenceBadge renders correct color for each threshold
- [ ] AuditPanel shows pipeline steps with durations — AC 6.3
- [ ] AuditPanel steps sorted by step_order
- [ ] All components have TypeScript props interfaces
- [ ] Each component file under 200 lines

## Files Changed

- `frontend/src/components/workspace/ExtractionPanel.tsx` — implement from stub
- `frontend/src/components/workspace/ConfidenceBadge.tsx` — implement from stub
- `frontend/src/components/workspace/AuditPanel.tsx` — new file
- `frontend/src/pages/Workspace.tsx` — wire AuditPanel to "audit" tab

## Verification

```bash
cd frontend
npm run typecheck
npm run lint
npm run dev
# Manual testing:
# 1. Open workspace with processed document → extraction table visible
# 2. Click table row → row highlighted, field highlighted on viewer
# 3. Toggle to JSON view → formatted JSON shown
# 4. Switch to Audit tab → pipeline steps visible with timing
# 5. Check ConfidenceBadge colors: 0.95 = green, 0.6 = yellow, 0.3 = red
# 6. Open workspace with unprocessed document → empty state messages
```
