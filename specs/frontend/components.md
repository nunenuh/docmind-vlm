# Frontend Spec: Components

Directory: `frontend/src/components/`

See also: [[projects/docmind-vlm/specs/frontend/state]] · [[projects/docmind-vlm/specs/frontend/api-client]]

---

## Component Tree

```
App.tsx                              <- Root layout + routing
├── pages/
│   ├── LandingPage.tsx              <- Public landing page (no auth)
│   │   ├── HeroSection.tsx
│   │   ├── FeatureShowcase.tsx
│   │   ├── HowItWorks.tsx
│   │   ├── TechStack.tsx
│   │   └── CallToAction.tsx
│   ├── DashboardPage.tsx            <- Document list (auth required)
│   │   ├── DocumentCard.tsx
│   │   └── UploadArea.tsx
│   └── WorkspacePage.tsx            <- Document workspace (auth required)
│       ├── DocumentViewer.tsx       <- Canvas-based renderer with overlays
│       ├── workspace/
│       │   ├── ExtractionPanel.tsx  <- Extracted fields + JSON view
│       │   ├── ChatPanel.tsx        <- Conversational Q&A
│       │   ├── AuditPanel.tsx       <- Pipeline transparency timeline
│       │   └── ComparePanel.tsx     <- Side-by-side comparison
│       └── ProcessingProgress.tsx   <- SSE step-by-step progress
└── components/
    ├── ui/                          <- shadcn/ui generated components
    ├── AuthGuard.tsx                <- Protect routes, redirect to login
    ├── ConfidenceBadge.tsx          <- Green/yellow/red confidence indicator
    └── CitationBlock.tsx            <- Clickable document citation
```

---

## Setup: shadcn/ui

Install components before building:

```bash
cd frontend

# 1. Init shadcn (if not already done)
npx shadcn@latest init

# 2. Add all components used in this project
npx shadcn@latest add card button badge input textarea
npx shadcn@latest add tabs scroll-area tooltip dialog
npx shadcn@latest add dropdown-menu progress separator
```

Generated components live in `src/components/ui/`. **Do not edit these files** unless customizing a component permanently — treat them as owned source code, not library files.

---

## File Conventions

### File naming
- Components: `PascalCase.tsx` (`DocumentViewer.tsx`, `ChatPanel.tsx`)
- Hooks: `camelCase.ts` (`useDocuments.ts`, `useSSEStream.ts`)
- shadcn generated: match shadcn output (`button.tsx`, `badge.tsx`)

### Props interface
Every component defines its own props interface, co-located in the same file:

```typescript
// Correct: interface co-located with component
interface UploadAreaProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
  progress: number;
}

export function UploadArea({ onUpload, isUploading, progress }: UploadAreaProps) {
  ...
}

// Wrong: unnamed inline prop type
export function UploadArea({ onUpload }: { onUpload: (f: File) => void }) {
```

### Component size
- Max 200 lines per component file
- If a component grows past 150 lines, extract subcomponents

---

## `UploadArea.tsx`

```typescript
/**
 * UploadArea — Drag-and-drop + file picker for document upload
 *
 * Props:
 *   onUpload    — called with the selected File when validation passes
 *   isUploading — true while upload is in progress
 *   progress    — upload progress 0–100
 */

import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, FileImage, X } from "lucide-react";

interface UploadAreaProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
  progress: number;
}

const ACCEPTED_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/tiff",
  "image/webp",
  "application/pdf",
]);
const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

export function UploadArea({ onUpload, isUploading, progress }: UploadAreaProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback((file: File): string | null => {
    if (!ACCEPTED_TYPES.has(file.type)) {
      return `Unsupported file type: ${file.type}. Accepted: PNG, JPEG, TIFF, WebP, PDF.`;
    }
    if (file.size > MAX_FILE_SIZE) {
      return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum: 20 MB.`;
    }
    return null;
  }, []);

  const handleFile = useCallback(
    (file: File) => {
      const validationError = validate(file);
      if (validationError) {
        setError(validationError);
        setSelectedFile(null);
        return;
      }
      setError(null);
      setSelectedFile(file);
      onUpload(file);
    },
    [validate, onUpload],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  const clearSelection = useCallback(() => {
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`
        border-2 border-dashed rounded-lg p-8 text-center transition-colors
        ${isDragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25"}
        ${isUploading ? "pointer-events-none opacity-60" : "cursor-pointer"}
      `}
      onClick={() => !isUploading && fileInputRef.current?.click()}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".png,.jpg,.jpeg,.tiff,.tif,.webp,.pdf"
        onChange={handleInputChange}
        className="hidden"
      />

      {isUploading ? (
        <div className="flex flex-col items-center gap-3">
          <Upload className="h-8 w-8 animate-pulse text-primary" />
          <p className="text-sm text-muted-foreground">Uploading...</p>
          <Progress value={progress} className="w-48" />
          <p className="text-xs text-muted-foreground">{progress}%</p>
        </div>
      ) : selectedFile ? (
        <div className="flex flex-col items-center gap-2">
          <FileImage className="h-8 w-8 text-primary" />
          <p className="text-sm font-medium">{selectedFile.name}</p>
          <p className="text-xs text-muted-foreground">
            {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
          </p>
          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); clearSelection(); }}>
            <X className="h-4 w-4 mr-1" /> Remove
          </Button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2">
          <Upload className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm font-medium">Drop a document here or click to browse</p>
          <p className="text-xs text-muted-foreground">PNG, JPEG, TIFF, WebP, PDF — max 20 MB</p>
        </div>
      )}

      {error && (
        <p className="mt-3 text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}
```

---

## `DocumentViewer.tsx`

```typescript
/**
 * DocumentViewer — Canvas-based document renderer with field overlays
 *
 * Props:
 *   imageUrl          — URL of the document image to render
 *   fields            — extracted fields with bounding box data
 *   overlayMode       — "none" | "confidence" | "bounding_box"
 *   onFieldClick      — called when user clicks a field overlay
 *   highlightedFieldId — field to highlight (synced with ExtractionPanel)
 */

import { useRef, useEffect, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import type { ExtractedFieldResponse } from "@/types/api";

interface DocumentViewerProps {
  imageUrl: string;
  fields: ExtractedFieldResponse[];
  overlayMode: "none" | "confidence" | "bounding_box";
  onFieldClick: (fieldId: string) => void;
  highlightedFieldId: string | null;
}

const CONFIDENCE_COLORS = {
  high: "rgba(34, 197, 94, 0.3)",   // green
  medium: "rgba(234, 179, 8, 0.3)", // yellow
  low: "rgba(239, 68, 68, 0.3)",    // red
};

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return CONFIDENCE_COLORS.high;
  if (confidence >= 0.5) return CONFIDENCE_COLORS.medium;
  return CONFIDENCE_COLORS.low;
}

export function DocumentViewer({
  imageUrl,
  fields,
  overlayMode,
  onFieldClick,
  highlightedFieldId,
}: DocumentViewerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // Load image
  useEffect(() => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      imageRef.current = img;
      draw();
    };
    img.src = imageUrl;
  }, [imageUrl]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const img = imageRef.current;
    if (!canvas || !ctx || !img) return;

    const container = containerRef.current;
    if (container) {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw document image
    const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
    const drawWidth = img.width * scale;
    const drawHeight = img.height * scale;
    const offsetX = (canvas.width / zoom - drawWidth) / 2;
    const offsetY = (canvas.height / zoom - drawHeight) / 2;
    ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);

    // Draw field overlays
    if (overlayMode !== "none") {
      for (const field of fields) {
        if (!field.bounding_box) continue;
        const { x, y, width, height } = field.bounding_box;
        const rx = offsetX + x * drawWidth;
        const ry = offsetY + y * drawHeight;
        const rw = width * drawWidth;
        const rh = height * drawHeight;

        const isHighlighted = field.field_id === highlightedFieldId;

        if (overlayMode === "confidence") {
          ctx.fillStyle = getConfidenceColor(field.confidence);
          ctx.fillRect(rx, ry, rw, rh);
        }

        ctx.strokeStyle = isHighlighted ? "#3b82f6" : "#64748b";
        ctx.lineWidth = isHighlighted ? 3 / zoom : 1 / zoom;
        ctx.strokeRect(rx, ry, rw, rh);

        if (isHighlighted) {
          ctx.fillStyle = "rgba(59, 130, 246, 0.1)";
          ctx.fillRect(rx, ry, rw, rh);
        }
      }
    }

    ctx.restore();
  }, [zoom, pan, fields, overlayMode, highlightedFieldId]);

  // Redraw on state changes
  useEffect(() => { draw(); }, [draw]);

  // Mouse handlers for panning
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsPanning(true);
    setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  }, [pan]);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!isPanning) return;
      setPan({ x: e.clientX - panStart.x, y: e.clientY - panStart.y });
    },
    [isPanning, panStart],
  );

  const handleMouseUp = useCallback(() => { setIsPanning(false); }, []);

  // Click detection for field selection
  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (isPanning) return;
      const canvas = canvasRef.current;
      const img = imageRef.current;
      if (!canvas || !img) return;

      const rect = canvas.getBoundingClientRect();
      const clickX = (e.clientX - rect.left - pan.x) / zoom;
      const clickY = (e.clientY - rect.top - pan.y) / zoom;

      const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
      const drawWidth = img.width * scale;
      const drawHeight = img.height * scale;
      const offsetX = (canvas.width / zoom - drawWidth) / 2;
      const offsetY = (canvas.height / zoom - drawHeight) / 2;

      for (const field of fields) {
        if (!field.bounding_box) continue;
        const { x, y, width, height } = field.bounding_box;
        const rx = offsetX + x * drawWidth;
        const ry = offsetY + y * drawHeight;
        const rw = width * drawWidth;
        const rh = height * drawHeight;

        if (clickX >= rx && clickX <= rx + rw && clickY >= ry && clickY <= ry + rh) {
          onFieldClick(field.field_id);
          return;
        }
      }
    },
    [fields, zoom, pan, isPanning, onFieldClick],
  );

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 5.0));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.25));
  const handleReset = () => { setZoom(1.0); setPan({ x: 0, y: 0 }); };

  return (
    <div ref={containerRef} className="relative w-full h-full bg-muted/20">
      {/* Zoom controls */}
      <div className="absolute top-2 right-2 z-10 flex gap-1">
        <Button variant="secondary" size="icon" onClick={handleZoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="secondary" size="icon" onClick={handleZoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button variant="secondary" size="icon" onClick={handleReset}>
          <RotateCcw className="h-4 w-4" />
        </Button>
      </div>

      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
      />
    </div>
  );
}
```

**DocumentViewer Rules:**
- Use `ResizeObserver`-ready container — canvas fills parent dimensions
- Overlay modes: `"none"` (no overlays), `"confidence"` (color-coded fill), `"bounding_box"` (outline only)
- Highlighted field gets blue border + subtle fill
- Zoom range: 0.25x to 5.0x, step 0.25
- Pan via mouse drag; click passthrough for field selection
- Bounding box coordinates are normalized (0.0-1.0) relative to image dimensions

---

## `ExtractionPanel.tsx`

```typescript
/**
 * ExtractionPanel — Extracted fields table with confidence badges + JSON toggle
 *
 * Props:
 *   extraction     — full extraction response (null while loading)
 *   onFieldSelect  — called when user clicks a field row
 *   selectedFieldId — currently selected field (highlight row)
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { ExtractionResponse } from "@/types/api";

interface ExtractionPanelProps {
  extraction: ExtractionResponse | null;
  onFieldSelect: (fieldId: string) => void;
  selectedFieldId: string | null;
}

export function ExtractionPanel({
  extraction,
  onFieldSelect,
  selectedFieldId,
}: ExtractionPanelProps) {
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
      {/* Header with view toggle */}
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

      {/* Table view */}
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
                  key={field.field_id}
                  onClick={() => onFieldSelect(field.field_id)}
                  className={`
                    border-b cursor-pointer transition-colors hover:bg-muted/50
                    ${field.field_id === selectedFieldId ? "bg-primary/10" : ""}
                  `}
                >
                  <td className="py-2 pr-3 font-medium">{field.field_name}</td>
                  <td className="py-2 pr-3 text-muted-foreground truncate max-w-[200px]">
                    {field.value ?? "—"}
                  </td>
                  <td className="py-2">
                    <ConfidenceBadge confidence={field.confidence} showValue />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollArea>
      )}

      {/* JSON view */}
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

---

## `ChatPanel.tsx`

```typescript
/**
 * ChatPanel — Conversational Q&A with document citations + SSE streaming
 *
 * Props:
 *   documentId     — current document for context
 *   onCitationClick — called when user clicks a citation reference
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CitationBlock } from "@/components/CitationBlock";
import { Send, Loader2 } from "lucide-react";
import { createSSEStream } from "@/lib/api";
import { useChatHistory } from "@/hooks/useChat";
import type { ChatMessageResponse, Citation } from "@/types/api";

interface ChatPanelProps {
  documentId: string;
  onCitationClick: (citation: Citation) => void;
}

export function ChatPanel({ documentId, onCitationClick }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [streamedCitations, setStreamedCitations] = useState<Citation[]>([]);
  const [messages, setMessages] = useState<ChatMessageResponse[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load existing chat history
  const { data: history } = useChatHistory(documentId);
  useEffect(() => {
    if (history) setMessages(history);
  }, [history]);

  // Auto-scroll on new content
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamedAnswer]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    // Add user message immediately
    const userMessage: ChatMessageResponse = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);
    setStreamedAnswer("");
    setStreamedCitations([]);

    const controller = createSSEStream(
      `/api/v1/chat/${documentId}`,
      { message: trimmed },
      (event) => {
        const data = event as { type: string; content?: string; citations?: Citation[] };
        if (data.type === "token") {
          setStreamedAnswer((prev) => prev + (data.content ?? ""));
        } else if (data.type === "citations") {
          setStreamedCitations(data.citations ?? []);
        } else if (data.type === "done") {
          // Finalize assistant message
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: data.content ?? "",
              citations: data.citations ?? [],
              created_at: new Date().toISOString(),
            },
          ]);
          setStreamedAnswer("");
          setStreamedCitations([]);
          setIsStreaming(false);
        }
      },
      (error) => {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${error.message}`,
            citations: [],
            created_at: new Date().toISOString(),
          },
        ]);
        setIsStreaming(false);
      },
      () => { setIsStreaming(false); },
    );

    abortRef.current = controller;
  }, [input, isStreaming, documentId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <ScrollArea className="flex-1 pr-2">
        <div className="flex flex-col gap-4 p-3">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`text-sm ${msg.role === "user" ? "text-right" : "text-left"}`}
            >
              <div
                className={`
                  inline-block rounded-lg px-3 py-2 max-w-[85%]
                  ${msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"}
                `}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.citations.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {msg.citations.map((cit, citIdx) => (
                      <CitationBlock
                        key={citIdx}
                        citation={cit}
                        onClick={() => onCitationClick(cit)}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Streaming indicator */}
          {isStreaming && streamedAnswer && (
            <div className="text-sm text-left">
              <div className="inline-block rounded-lg px-3 py-2 max-w-[85%] bg-muted">
                <p className="whitespace-pre-wrap">{streamedAnswer}</p>
                {streamedCitations.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {streamedCitations.map((cit, idx) => (
                      <CitationBlock key={idx} citation={cit} onClick={() => onCitationClick(cit)} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      {/* Input area */}
      <div className="flex gap-2 p-3 border-t">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about this document..."
          disabled={isStreaming}
          rows={2}
          className="resize-none"
        />
        <Button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          size="icon"
          className="self-end"
        >
          {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}
```

---

## `ConfidenceBadge.tsx`

```typescript
/**
 * ConfidenceBadge — Reusable color-coded confidence indicator
 *
 * Props:
 *   confidence — value between 0.0 and 1.0
 *   showValue  — if true, display the numeric value (default: false)
 */

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
      {showValue
        ? `${(confidence * 100).toFixed(0)}%`
        : threshold.label}
    </Badge>
  );
}
```

**Confidence color rules:**
| Range | Color | Label |
|-------|-------|-------|
| >= 0.8 | Green | High |
| 0.5 - 0.79 | Yellow | Medium |
| < 0.5 | Red | Low |

---

## `ComparePanel.tsx`

```typescript
/**
 * ComparePanel — Side-by-side extraction comparison with color-coded diffs
 *
 * Props:
 *   comparison — comparison response (null while loading)
 */

import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import type { ComparisonResponse } from "@/types/api";

interface ComparePanelProps {
  comparison: ComparisonResponse | null;
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

  return (
    <div className="flex flex-col h-full gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Extraction Comparison</h3>
        <div className="flex gap-2 text-xs">
          <Badge variant="outline" className="border-blue-500 text-blue-700">Corrected</Badge>
          <Badge variant="outline" className="border-green-500 text-green-700">Added</Badge>
          <Badge variant="outline" className="border-red-500 text-red-700">Removed</Badge>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="grid grid-cols-2 gap-4">
          {/* Left column: Raw extraction */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Raw Extraction</p>
            <div className="flex flex-col gap-1">
              {comparison.diffs.map((diff) => (
                <div
                  key={diff.field_name}
                  className={`rounded px-2 py-1.5 text-sm ${DIFF_COLORS[diff.status]}`}
                >
                  <span className="font-medium">{diff.field_name}:</span>{" "}
                  <span className="text-muted-foreground">{diff.raw_value ?? "—"}</span>
                  {diff.raw_confidence !== null && (
                    <ConfidenceBadge confidence={diff.raw_confidence} showValue className="ml-2" />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Right column: Post-processed */}
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-2">Post-Processed</p>
            <div className="flex flex-col gap-1">
              {comparison.diffs.map((diff) => (
                <div
                  key={diff.field_name}
                  className={`rounded px-2 py-1.5 text-sm ${DIFF_COLORS[diff.status]}`}
                >
                  <span className="font-medium">{diff.field_name}:</span>{" "}
                  <span className="text-muted-foreground">{diff.final_value ?? "—"}</span>
                  {diff.final_confidence !== null && (
                    <ConfidenceBadge confidence={diff.final_confidence} showValue className="ml-2" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}
```

**Diff color rules:**
| Status | Color | Meaning |
|--------|-------|---------|
| `corrected` | Blue left border | Value changed by post-processing |
| `added` | Green left border | Field added by post-processing |
| `removed` | Red left border | Field removed by post-processing |
| `unchanged` | No highlight | Same in raw and final |

---

## `ProcessingProgress.tsx`

```typescript
/**
 * ProcessingProgress — SSE-powered step-by-step processing visualization
 *
 * Props:
 *   documentId — document being processed
 *   onComplete — called when processing finishes
 */

import { useState, useEffect, useRef } from "react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Loader2, Circle } from "lucide-react";
import { processDocument } from "@/lib/api";

interface ProcessingProgressProps {
  documentId: string;
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
    case "complete":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "active":
      return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
    case "error":
      return <Circle className="h-4 w-4 text-destructive" />;
    default:
      return <Circle className="h-4 w-4 text-muted-foreground" />;
  }
}

export function ProcessingProgress({ documentId, onComplete }: ProcessingProgressProps) {
  const [steps, setSteps] = useState<ProcessingStep[]>(INITIAL_STEPS);
  const [overallProgress, setOverallProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const eventSource = processDocument(documentId);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data) as {
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
        eventSource.close();
        onComplete();
      }
    };

    eventSource.onerror = () => {
      setError("Connection lost. Processing may still be running.");
      eventSource.close();
    };

    return () => { eventSource.close(); };
  }, [documentId, onComplete]);

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

      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}
    </div>
  );
}
```

---

## `CitationBlock.tsx`

```typescript
/**
 * CitationBlock — Clickable document citation reference
 *
 * Props:
 *   citation — citation data with page, region, and text
 *   onClick  — called when user clicks the citation
 */

import { FileText } from "lucide-react";
import type { Citation } from "@/types/api";

interface CitationBlockProps {
  citation: Citation;
  onClick: () => void;
}

export function CitationBlock({ citation, onClick }: CitationBlockProps) {
  return (
    <button
      onClick={onClick}
      className="flex items-start gap-2 text-xs text-left rounded px-2 py-1.5 bg-primary/5 hover:bg-primary/10 transition-colors border border-primary/20 w-full"
    >
      <FileText className="h-3 w-3 mt-0.5 text-primary shrink-0" />
      <div>
        <span className="font-medium text-primary">
          Page {citation.page}{citation.region ? `, ${citation.region}` : ""}
        </span>
        {citation.text && (
          <p className="text-muted-foreground mt-0.5 line-clamp-2">{citation.text}</p>
        )}
      </div>
    </button>
  );
}
```

---

## `AuthGuard.tsx`

```typescript
/**
 * AuthGuard — Protect routes that require authentication
 *
 * Wraps child routes. Redirects to landing page if no active session.
 * Shows loading spinner while checking auth state.
 */

import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";
import { Loader2 } from "lucide-react";
import type { Session } from "@supabase/supabase-js";

interface AuthGuardProps {
  children: React.ReactNode;
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check current session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setIsLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => { setSession(s); },
    );

    return () => { subscription.unsubscribe(); };
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
```

---

## shadcn/ui Component Usage Rules

| shadcn Component | Where Used | Key Props |
|-----------------|------------|-----------|
| `Card` | DocumentCard, panel containers | `className="h-full"` for full-height |
| `Button` | Upload, chat send, zoom controls | `disabled={isLoading}` |
| `Badge` | Confidence, diff status, field count | Custom `className` for color override |
| `Input` | Search, filter | `onKeyDown` for Enter key submit |
| `Textarea` | Chat input | `rows={2} className="resize-none"` |
| `Tabs` | Workspace panels, table/JSON toggle | Controlled with `value` + `onValueChange` |
| `ScrollArea` | Chat messages, extraction table | Wrap scrollable content |
| `Tooltip` | Icon buttons, truncated text | Wrap interactive elements |
| `Dialog` | Delete confirmation, template select | Controlled with `open` + `onOpenChange` |
| `Progress` | Upload progress, processing progress | `value={0-100}` |
| `Separator` | Panel dividers | Between logical sections |
| `DropdownMenu` | Document actions (rename, delete) | Attach to three-dot icon button |

**Tailwind class rule**: Use Tailwind classes directly. Do not write custom CSS files unless absolutely necessary (shadcn's CSS variables handle theming).

---

## TypeScript Rules

```typescript
// Always define prop interface
interface ComponentProps { ... }
export function Component(props: ComponentProps) { ... }

// Use type imports
import type { ExtractionResponse, Citation } from "@/types/api";

// Never use `any` in component code
const handler = (e: any) => ...   // WRONG

// Use proper event types
const handler = (e: React.ChangeEvent<HTMLInputElement>) => ...  // CORRECT
const handler = (e: React.DragEvent<HTMLDivElement>) => ...      // CORRECT
const handler = (e: React.KeyboardEvent<HTMLTextAreaElement>) => ... // CORRECT

// Use Set for ID lookups (O(1))
highlightedIds: Set<string>   // CORRECT — not string[]

// Prefer const assertions for static config
const THRESHOLDS = { ... } as const;
```

---

## Project Components

The project feature introduces multi-document knowledge bases with persona-driven RAG chat. These components live alongside the existing document workspace components.

### Updated Component Tree (additions only)

```
App.tsx
├── pages/
│   ├── ProjectDashboardPage.tsx        <- Project list (auth required)
│   │   └── ProjectCard.tsx
│   └── ProjectWorkspacePage.tsx        <- Project workspace (auth required)
│       ├── ProjectDocumentList.tsx      <- Left panel: project documents
│       ├── ProjectChatPanel.tsx         <- Right panel: RAG chat
│       └── PersonaSelector.tsx          <- Header: persona dropdown
└── components/
    └── PersonaEditor.tsx               <- Modal: create/edit persona
```

---

### `ProjectDashboardPage.tsx`

```typescript
/**
 * ProjectDashboardPage — Grid of user's projects with creation action
 *
 * Props: none (page component, data fetched internally via hooks)
 *
 * Layout:
 *   - Header with title + "New Project" button
 *   - Responsive card grid (1-col mobile, 2-col tablet, 3-col desktop)
 *   - Each ProjectCard shows: project name, doc count, persona name, last updated
 *   - Click card → navigates to /projects/:id (ProjectWorkspacePage)
 *   - Empty state when no projects exist
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Plus, FolderOpen, FileText, Bot } from "lucide-react";
import { useProjects, useCreateProject } from "@/hooks/useProjects";
import type { ProjectResponse } from "@/types/api";

interface ProjectCardProps {
  project: ProjectResponse;
  onClick: () => void;
}

function ProjectCard({ project, onClick }: ProjectCardProps) {
  return (
    <Card
      onClick={onClick}
      className="p-4 cursor-pointer hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-sm font-semibold truncate">{project.name}</h3>
        <Badge variant="secondary" className="text-xs shrink-0 ml-2">
          <FileText className="h-3 w-3 mr-1" />
          {project.document_count}
        </Badge>
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Bot className="h-3 w-3" />
        <span className="truncate">{project.persona_name ?? "Default"}</span>
      </div>
      <p className="text-xs text-muted-foreground mt-2">
        Updated {new Date(project.updated_at).toLocaleDateString()}
      </p>
    </Card>
  );
}
```

**ProjectDashboardPage Rules:**
- Fetches projects via `useProjects()` hook (React Query)
- "New Project" opens a `Dialog` with name input + optional persona selection
- Cards are read-only summaries — no inline editing on the dashboard
- Uses `useNavigate()` for client-side routing to workspace

---

### `ProjectWorkspacePage.tsx`

```typescript
/**
 * ProjectWorkspacePage — Split-panel project workspace
 *
 * Props: none (page component, project ID from route params)
 *
 * Layout:
 *   - Header: project name, PersonaSelector dropdown, settings gear icon
 *   - Left panel (resizable, ~35%): ProjectDocumentList
 *   - Right panel (~65%): ProjectChatPanel
 *   - Upload docs via drag-and-drop into the left panel
 */

import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Settings } from "lucide-react";
import { PersonaSelector } from "@/components/PersonaSelector";
import { ProjectDocumentList } from "./ProjectDocumentList";
import { ProjectChatPanel } from "./ProjectChatPanel";
import { useProject } from "@/hooks/useProjects";

// Route: /projects/:projectId
```

**ProjectWorkspacePage Rules:**
- Project ID extracted from route params via `useParams()`
- Left/right panels use CSS `grid-cols-[35%_1fr]` or a resizable splitter
- Header persona selector updates the project's active persona
- Settings gear opens project settings (rename, delete, persona config)

---

### `PersonaSelector.tsx`

```typescript
/**
 * PersonaSelector — Dropdown for selecting a project's active persona
 *
 * Props:
 *   projectId     — current project
 *   selectedId    — currently active persona ID (null = default)
 *   onSelect      — called when user picks a persona
 *   onCustomize   — called when user clicks "Customize" (opens PersonaEditor)
 */

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Bot, ChevronDown, Pencil } from "lucide-react";
import { usePersonas } from "@/hooks/usePersonas";

interface PersonaSelectorProps {
  projectId: string;
  selectedId: string | null;
  onSelect: (personaId: string) => void;
  onCustomize: () => void;
}

export function PersonaSelector({
  projectId,
  selectedId,
  onSelect,
  onCustomize,
}: PersonaSelectorProps) {
  const { data: personas } = usePersonas();

  const selected = personas?.find((p) => p.id === selectedId);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Bot className="h-4 w-4" />
          <span className="truncate max-w-[150px]">
            {selected?.name ?? "Default Persona"}
          </span>
          <ChevronDown className="h-3 w-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        {personas?.map((persona) => (
          <DropdownMenuItem
            key={persona.id}
            onClick={() => onSelect(persona.id)}
            className="flex flex-col items-start"
          >
            <span className="font-medium text-sm">{persona.name}</span>
            <span className="text-xs text-muted-foreground line-clamp-1">
              {persona.description}
            </span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={onCustomize} className="gap-2">
          <Pencil className="h-3 w-3" />
          Customize
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

**PersonaSelector Rules:**
- Fetches personas via `usePersonas()` hook — includes both preset and user-created personas
- Each item shows persona name + short description (one-line clamp)
- "Customize" item at the bottom opens `PersonaEditor` modal
- Selecting a persona calls `onSelect` — parent component persists the change

---

### `PersonaEditor.tsx`

```typescript
/**
 * PersonaEditor — Modal for creating or editing a persona
 *
 * Props:
 *   persona   — existing persona to edit (null = create new)
 *   open      — controlled dialog open state
 *   onClose   — called on cancel or after save
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";
import { useSavePersona } from "@/hooks/usePersonas";
import type { PersonaResponse } from "@/types/api";

interface PersonaEditorProps {
  persona: PersonaResponse | null;
  open: boolean;
  onClose: () => void;
}

// Fields:
//   name          — text input, required
//   description   — text input, short summary
//   system_prompt — textarea, the persona's system prompt
//   tone          — select: "professional" | "friendly" | "technical" | "concise"
//   rules         — tag input (array of strings), persona behavioral rules
//   boundaries    — tag input (array of strings), topics the persona should avoid
//
// Footer:
//   - Preview section showing a sample prompt rendered with the persona config
//   - Cancel button (closes modal, discards changes)
//   - Save button (calls useSavePersona mutation, then onClose)
```

**PersonaEditor Rules:**
- Tag inputs for `rules` and `boundaries` — type text + Enter to add, click X to remove
- `tone` uses a `<select>` or shadcn `Select` component with preset options
- Preview section renders a mock prompt: system_prompt + a sample user question to show how the persona will frame responses
- Save triggers `useSavePersona` mutation (POST for new, PUT for existing)
- All fields validate on submit — `name` and `system_prompt` are required

---

### `ProjectChatPanel.tsx`

```typescript
/**
 * ProjectChatPanel — RAG chat panel with conversation management
 *
 * Props:
 *   projectId — current project for RAG context
 *   personaId — active persona (null = default)
 *
 * Differences from ChatPanel:
 *   - Left sidebar: conversation list with "New conversation" button
 *   - Citations show document name + page number (not just page)
 *   - Persona name displayed at top of chat area
 *   - Sends to project RAG chat endpoint, not per-document VLM chat
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Send, Loader2, Plus, MessageSquare, FileText } from "lucide-react";
import { createSSEStream } from "@/lib/api";
import { useProjectConversations, useConversationHistory } from "@/hooks/useProjectChat";
import type { ProjectChatMessageResponse, ProjectCitation } from "@/types/api";

interface ProjectChatPanelProps {
  projectId: string;
  personaId: string | null;
}

// Layout:
//   ┌──────────────┬──────────────────────────────────────┐
//   │ Conversations│  Persona: "Research Analyst"         │
//   │              │──────────────────────────────────────│
//   │ + New        │                                      │
//   │              │  [message list with citations]        │
//   │ Conv 1       │                                      │
//   │ Conv 2       │                                      │
//   │ Conv 3       │──────────────────────────────────────│
//   │              │  [input area]                        │
//   └──────────────┴──────────────────────────────────────┘
//
// Citation format:
//   <CitationBlock>
//     📄 invoice_march.pdf — Page 3
//     "Total amount due: $1,250.00"
//   </CitationBlock>
```

**ProjectChatPanel Rules:**
- Conversation sidebar lists all conversations for this project via `useProjectConversations()`
- "New conversation" button creates a fresh thread (new `conversation_id`)
- Messages stream via SSE from `POST /api/v1/projects/{projectId}/chat`
- Citations include `document_name` and `page_number` — rendered as "filename — Page N"
- Persona name displayed as a header badge above the message list
- Input placeholder: "Ask about your documents..."

---

### `ProjectDocumentList.tsx`

```typescript
/**
 * ProjectDocumentList — Document list panel for a project
 *
 * Props:
 *   projectId — current project
 */

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Upload, Trash2, FileText, CheckCircle2, Loader2 } from "lucide-react";
import { useProjectDocuments, useUploadProjectDocument, useDeleteProjectDocument } from "@/hooks/useProjectDocuments";
import type { ProjectDocumentResponse } from "@/types/api";

interface ProjectDocumentListProps {
  projectId: string;
}

// Each document row shows:
//   - File icon + filename (truncated)
//   - Page count badge
//   - Chunk count badge (number of indexed chunks)
//   - Indexed status: green check (indexed) or spinner (processing)
//   - Delete button (with confirmation)
//
// Bottom section:
//   - Upload button
//   - Drag-and-drop area (reuses UploadArea pattern)
//   - Accepts PDF files, max 20 MB each
```

**ProjectDocumentList Rules:**
- Fetches documents via `useProjectDocuments(projectId)` hook
- Upload triggers chunking + embedding pipeline on the backend
- Indexed status reflects whether all chunks have embeddings in pgvector
- Delete button shows a confirmation `Dialog` before removing
- Drag-and-drop zone at the bottom of the list, styled consistently with `UploadArea`
- Multiple file upload supported — files are uploaded sequentially
