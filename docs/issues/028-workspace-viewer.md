# Issue #28: Workspace Page Layout + DocumentViewer

## Summary

Implement the Workspace page with a split-panel layout: DocumentViewer on the left (canvas-based document renderer with zoom/pan and field overlay support) and a tabbed sidebar on the right (Extraction, Chat, Audit, Compare tabs). Wire up the workspace-store (Zustand) for activeTab, overlayMode, zoomLevel, selectedFieldId, and isProcessing state. The DocumentViewer renders the document image on a canvas, draws bounding box overlays with confidence-based coloring, supports zoom (0.25x-5.0x) and pan via mouse drag, and highlights selected fields synced from the sidebar.

## Context

- **Phase**: 6 — Frontend
- **Priority**: P0
- **Labels**: `phase-6-frontend`, `frontend`, `tdd`
- **Dependencies**: #26 (AuthGuard), #27 (Dashboard navigates here)
- **Branch**: `feat/28-workspace-viewer`
- **Estimated scope**: L

## Specs to Read

- `specs/frontend/components.md` — DocumentViewer full implementation with canvas rendering, overlay modes, zoom/pan
- `specs/frontend/state.md` — workspace-store (activeTab, overlayMode, selectedFieldId, zoomLevel), query invalidation after processing
- `specs/frontend/api-client.md` — fetchDocument, fetchExtraction, fetchOverlay, processDocument
- `docs/blueprint/02-product/user-interface-specification.md` — Sections 2.3 (Workspace), 2.4 (Document Viewer)
- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 6.1, AC 7.1-7.3

## Current State (Scaffold)

**File: `frontend/src/pages/Workspace.tsx`**
```typescript
export function Workspace() {
  return <div className="min-h-screen p-8"><h1 className="text-2xl font-bold">Workspace</h1></div>;
}
```

**File: `frontend/src/components/workspace/DocumentViewer.tsx`**
```typescript
export function DocumentViewer() {
  return <div>DocumentViewer</div>;
}
```

**File: `frontend/src/stores/workspace-store.ts`** (already implemented):
```typescript
export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeTab: "extraction" as const,
  overlayMode: "none" as const,
  selectedFieldId: null,
  zoomLevel: 1.0,
  isProcessing: false,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setOverlayMode: (mode) => set({ overlayMode: mode }),
  selectField: (fieldId) => set({ selectedFieldId: fieldId }),
  setZoomLevel: (level) => set({ zoomLevel: Math.max(0.25, Math.min(5.0, level)) }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  resetWorkspace: () => set(INITIAL_STATE),
}));
```

## Requirements

### Functional

1. **Split Layout**: Left panel = DocumentViewer (60% width), right panel = tabbed sidebar (40% width). Responsive: stacked on tablet/mobile.
2. **DocumentViewer**:
   - Render document image on HTML5 canvas, fitting container dimensions
   - Zoom controls: zoom in (+0.25), zoom out (-0.25), reset. Range 0.25x to 5.0x
   - Pan via mouse drag (cursor changes to grab/grabbing)
   - Overlay modes: "none" (clean image), "confidence" (color-coded fill per field), "bounding_box" (outline only)
   - Confidence colors: green (>= 0.8), yellow (>= 0.5), red (< 0.5)
   - Highlighted field: blue border + subtle fill when `highlightedFieldId` matches
   - Click on field bounding box region triggers `onFieldClick(fieldId)` callback
   - Bounding box coordinates are normalized (0.0-1.0)
3. **Tab Navigation**: Four tabs in sidebar: Extraction, Chat, Audit, Compare. Active tab stored in `workspace-store.activeTab`. Tab content renders respective panel component (stubs for now, implemented in issues #29, #30, #31).
4. **Overlay Mode Toggle**: Buttons or dropdown to switch between "none", "confidence", "bounding_box" modes.
5. **Workspace Reset**: When documentId changes (from URL params), call `resetWorkspace()` to clear stale state.
6. **Processing Trigger**: "Process" button visible when document status is "uploaded". Clicking triggers `processDocument` SSE stream and shows `ProcessingProgress` overlay.
7. **Top Bar**: Document filename, overlay mode toggle, back-to-dashboard button.

### Non-Functional

- Canvas redraws efficiently on state changes (debounce resize events)
- ResizeObserver handles container dimension changes
- Image loaded with crossOrigin="anonymous" for canvas security
- No layout shift during loading

## Implementation Plan

### Layout Structure

**`frontend/src/pages/Workspace.tsx`**:
```typescript
import { useParams } from "react-router-dom";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { DocumentViewer } from "@/components/workspace/DocumentViewer";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { useExtraction } from "@/hooks/useExtraction";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ExtractionPanel } from "@/components/workspace/ExtractionPanel";
import { ChatPanel } from "@/components/workspace/ChatPanel";
// AuditPanel and ComparePanel imported similarly

export function Workspace() {
  const { documentId } = useParams<{ documentId: string }>();
  const { activeTab, setActiveTab, overlayMode, selectedFieldId, selectField, resetWorkspace } = useWorkspaceStore();
  const { data: extraction } = useExtraction(documentId ?? "");

  // Reset workspace when switching documents
  useEffect(() => {
    resetWorkspace();
  }, [documentId, resetWorkspace]);

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <header className="h-12 border-b flex items-center px-4 gap-4">
        {/* Document name, overlay toggle, back button */}
      </header>

      {/* Split panels */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Left: DocumentViewer */}
        <div className="flex-1 md:w-3/5 min-h-0">
          <DocumentViewer
            imageUrl={imageUrl}
            fields={extraction?.fields ?? []}
            overlayMode={overlayMode}
            onFieldClick={selectField}
            highlightedFieldId={selectedFieldId}
          />
        </div>

        {/* Right: Tabbed sidebar */}
        <div className="md:w-2/5 border-l flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
            <TabsList className="w-full justify-start px-2 h-10">
              <TabsTrigger value="extraction">Extraction</TabsTrigger>
              <TabsTrigger value="chat">Chat</TabsTrigger>
              <TabsTrigger value="audit">Audit</TabsTrigger>
              <TabsTrigger value="compare">Compare</TabsTrigger>
            </TabsList>
            <TabsContent value="extraction" className="flex-1 overflow-auto p-3">
              <ExtractionPanel extraction={extraction ?? null} onFieldSelect={selectField} selectedFieldId={selectedFieldId} />
            </TabsContent>
            <TabsContent value="chat" className="flex-1 overflow-auto p-3">
              <ChatPanel documentId={documentId ?? ""} onCitationClick={() => {}} />
            </TabsContent>
            {/* audit and compare tabs */}
          </Tabs>
        </div>
      </div>
    </div>
  );
}
```

### DocumentViewer Implementation

**`frontend/src/components/workspace/DocumentViewer.tsx`** (implement per spec):
```typescript
interface DocumentViewerProps {
  imageUrl: string;
  fields: ExtractedFieldResponse[];
  overlayMode: "none" | "confidence" | "bounding_box";
  onFieldClick: (fieldId: string) => void;
  highlightedFieldId: string | null;
}

// Canvas rendering approach:
// 1. Load image into HTMLImageElement
// 2. On draw(): clear canvas, apply pan/zoom transforms, draw image scaled to fit
// 3. If overlayMode !== "none": iterate fields, draw bounding box rectangles
// 4. Confidence mode: fillRect with semi-transparent color based on confidence
// 5. Highlighted field: blue border (3px) + subtle blue fill
// 6. Mouse handlers: mousedown starts pan, mousemove updates pan, mouseup ends
// 7. Click handler: transforms click coordinates back to image space, hit-tests fields
// 8. Zoom buttons: setZoom with clamping to [0.25, 5.0]
```

Key canvas rendering details from the spec:
- Scale image to fit container: `Math.min(canvas.width / img.width, canvas.height / img.height)`
- Center image in canvas
- Bounding box coords are normalized (0.0-1.0), multiply by drawWidth/drawHeight
- Apply pan offset and zoom scale via `ctx.translate(pan.x, pan.y)` then `ctx.scale(zoom, zoom)`

### shadcn/ui Components Needed

```bash
cd frontend
npx shadcn@latest add tabs button tooltip dropdown-menu separator
```

### State Flow

```
URL: /workspace/:documentId
  → Workspace mounts, reads documentId from useParams
  → resetWorkspace() clears previous state
  → useExtraction(documentId) fetches extraction data
  → DocumentViewer renders image + overlays from extraction.fields
  → User clicks field on canvas → selectField(fieldId) → workspace-store updates
  → ExtractionPanel reads selectedFieldId → highlights row
  → User clicks row in ExtractionPanel → selectField(fieldId) → DocumentViewer highlights box
```

## Acceptance Criteria

- [ ] Split-panel layout: viewer left, tabbed sidebar right
- [ ] DocumentViewer renders document image on canvas
- [ ] Zoom in/out/reset controls work (0.25x to 5.0x range)
- [ ] Pan via mouse drag works
- [ ] Overlay mode "confidence" shows color-coded field overlays — AC 7.1, AC 7.2
- [ ] Overlay mode "bounding_box" shows outlines only
- [ ] Clicking a field region on canvas triggers onFieldClick — AC 6.1
- [ ] Highlighted field shows blue border + fill
- [ ] Tab navigation switches between Extraction, Chat, Audit, Compare
- [ ] Workspace state resets when documentId changes
- [ ] Responsive: stacked layout on tablet/mobile
- [ ] Canvas handles container resize via ResizeObserver
- [ ] All TypeScript interfaces defined for props

## Files Changed

- `frontend/src/pages/Workspace.tsx` — full split-layout implementation
- `frontend/src/components/workspace/DocumentViewer.tsx` — implement from stub (full canvas renderer)
- `frontend/src/stores/workspace-store.ts` — no changes (already correct)
- `frontend/src/hooks/useExtraction.ts` — no changes (already correct)

## Verification

```bash
cd frontend
npm run typecheck
npm run lint
npm run dev
# Manual testing:
# 1. Navigate to /workspace/:id → split layout visible
# 2. Document image renders on canvas
# 3. Zoom in/out buttons work, zoom level displayed
# 4. Drag to pan document
# 5. Toggle overlay modes → confidence colors appear
# 6. Click field on canvas → field highlighted
# 7. Switch tabs → correct panel content shows
# 8. Resize browser → canvas redraws correctly
# 9. Navigate to different document → workspace resets
```
