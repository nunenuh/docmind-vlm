# Issue #30: ChatPanel — Message Thread, SSE Streaming, Citations

## Summary

Implement the ChatPanel component with a scrollable message thread, text input area, SSE streaming for real-time response display, and inline CitationBlock components. When the user sends a message, it POSTs to `/api/v1/chat/:documentId` via the `createSSEStream` helper. Tokens stream in and render progressively. Completed messages include citations that, when clicked, highlight the referenced region on the DocumentViewer. Uses `useChatHistory` for loading previous messages and `useInvalidateChatHistory` to refresh after new messages.

## Context

- **Phase**: 6 — Frontend
- **Priority**: P0
- **Labels**: `phase-6-frontend`, `frontend`, `tdd`
- **Dependencies**: #28 (Workspace layout provides the Chat tab)
- **Branch**: `feat/30-chat-panel`
- **Estimated scope**: M

## Specs to Read

- `specs/frontend/components.md` — ChatPanel full implementation, CitationBlock component
- `specs/frontend/state.md` — useChatHistory hook, useInvalidateChatHistory
- `specs/frontend/api-client.md` — createSSEStream, sendChatMessage, SSE event format, Citation type
- `docs/blueprint/02-product/user-interface-specification.md` — Section 2.6 (Chat Tab)
- `docs/blueprint/02-product/acceptance-criteria-specification.md` — AC 9.1-9.6

## Current State (Scaffold)

**File: `frontend/src/components/workspace/ChatPanel.tsx`**
```typescript
export function ChatPanel() {
  return <div>ChatPanel</div>;
}
```

**File: `frontend/src/components/workspace/CitationBlock.tsx`**
```typescript
export function CitationBlock() {
  return <div>CitationBlock</div>;
}
```

**Hooks already implemented:**
```typescript
// frontend/src/hooks/useChat.ts
export function useChatHistory(documentId: string, page = 1, limit = 50) {
  return useQuery<ChatHistoryResponse>({
    queryKey: ["chat-history", documentId, page, limit],
    queryFn: () => fetchChatHistory(documentId, page, limit),
    enabled: !!documentId,
  });
}

export function useInvalidateChatHistory(documentId: string) {
  const queryClient = useQueryClient();
  return () => { queryClient.invalidateQueries({ queryKey: ["chat-history", documentId] }); };
}
```

**API already implemented:**
```typescript
// frontend/src/lib/api.ts
export function sendChatMessage(
  documentId: string, message: string,
  onMessage: (data: unknown) => void, onError: (error: Error) => void, onComplete: () => void,
): AbortController { ... }

export function createSSEStream(
  path: string, body: Record<string, unknown>,
  onMessage: (data: unknown) => void, onError: (error: Error) => void, onComplete: () => void,
): AbortController { ... }
```

**Types:**
```typescript
// frontend/src/types/api.ts
export interface Citation {
  page: number;
  bounding_box: BoundingBox;
  text_span: string;
}

export interface ChatMessageResponse {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
}
```

## Requirements

### Functional

1. **Message Thread**: Scrollable list of messages. User messages right-aligned with primary background. Assistant messages left-aligned with muted background.
2. **Chat Input**: Textarea (2 rows, non-resizable) with send button. Enter sends (Shift+Enter for newline). Disabled during streaming.
3. **SSE Streaming**: After sending, tokens stream in progressively. The `onMessage` callback handles three event types:
   - `type: "token"` — append `content` to streamed answer
   - `type: "citations"` — update streamed citations
   - `type: "done"` — finalize message, add to message list, clear stream state
4. **CitationBlock**: Clickable inline block showing page number, region, and text snippet. Clicking calls `onCitationClick(citation)` which should highlight the cited region on the DocumentViewer.
5. **Chat History**: Load existing messages on mount via `useChatHistory`. New messages added to local state. After stream completes, invalidate chat history query.
6. **Auto-scroll**: Scroll to bottom on new messages and during streaming.
7. **Abort**: Store AbortController ref. Cleanup on unmount or new message.
8. **Error Handling**: On stream error, show error message as assistant message.

### Non-Functional

- Streaming display feels responsive (no buffering delay)
- Chat available only after extraction completes — AC 9.1
- Response time < 3 seconds — AC 9.5
- Multi-turn context retained — AC 9.4
- History persists and loads when returning — AC 9.6

## Implementation Plan

### ChatPanel

**`frontend/src/components/workspace/ChatPanel.tsx`**:
```typescript
import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CitationBlock } from "@/components/workspace/CitationBlock";
import { Send, Loader2 } from "lucide-react";
import { sendChatMessage } from "@/lib/api";
import { useChatHistory, useInvalidateChatHistory } from "@/hooks/useChat";
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

  const { data: history } = useChatHistory(documentId);
  const invalidateHistory = useInvalidateChatHistory(documentId);

  // Load history
  useEffect(() => {
    if (history?.items) setMessages(history.items);
  }, [history]);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamedAnswer]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

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

    const controller = sendChatMessage(
      documentId,
      trimmed,
      (event) => {
        const data = event as { type: string; content?: string; citations?: Citation[] };
        if (data.type === "token") {
          setStreamedAnswer((prev) => prev + (data.content ?? ""));
        } else if (data.type === "citations") {
          setStreamedCitations(data.citations ?? []);
        } else if (data.type === "done") {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: data.content ?? "",
              citations: data.citations ?? [],
              created_at: new Date().toISOString(),
            },
          ]);
          setStreamedAnswer("");
          setStreamedCitations([]);
          setIsStreaming(false);
          invalidateHistory();
        }
      },
      (error) => {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
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
  }, [input, isStreaming, documentId, invalidateHistory]);

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
      <ScrollArea className="flex-1 pr-2">
        <div className="flex flex-col gap-4 p-3">
          {messages.map((msg) => (
            <div key={msg.id} className={`text-sm ${msg.role === "user" ? "text-right" : "text-left"}`}>
              <div className={`inline-block rounded-lg px-3 py-2 max-w-[85%] ${
                msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted"
              }`}>
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.citations.length > 0 && (
                  <div className="mt-2 flex flex-col gap-1">
                    {msg.citations.map((cit, idx) => (
                      <CitationBlock key={idx} citation={cit} onClick={() => onCitationClick(cit)} />
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
              </div>
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>
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
        <Button onClick={handleSend} disabled={isStreaming || !input.trim()} size="icon" className="self-end">
          {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}
```

### CitationBlock

**`frontend/src/components/workspace/CitationBlock.tsx`**:
```typescript
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
        <span className="font-medium text-primary">Page {citation.page}</span>
        {citation.text_span && (
          <p className="text-muted-foreground mt-0.5 line-clamp-2">{citation.text_span}</p>
        )}
      </div>
    </button>
  );
}
```

### Citation Click → DocumentViewer Highlight

When `onCitationClick(citation)` is called in the Workspace:
```typescript
// In Workspace.tsx
const handleCitationClick = (citation: Citation) => {
  // Convert citation bounding_box to a highlight on DocumentViewer
  // Could set a temporary overlay or scroll to the cited region
  // For now: set selectedFieldId to null and add a temporary highlight
  // Implementation depends on DocumentViewer supporting citation highlights
};
```

### SSE Event Format

The SSE stream from `/api/v1/chat/:documentId` sends these event types:
```json
{"type": "token", "content": "Based on"}
{"type": "token", "content": " the document"}
{"type": "citations", "citations": [{"page": 1, "bounding_box": {...}, "text_span": "..."}]}
{"type": "done", "content": "Based on the document, the total is $1,500.", "citations": [...]}
```

## Acceptance Criteria

- [ ] Chat input available after extraction completes — AC 9.1
- [ ] Chat responses include citation blocks with page number and text span — AC 9.2
- [ ] Clicking a citation highlights the referenced region on DocumentViewer — AC 9.3
- [ ] Multi-turn conversation retains context — AC 9.4
- [ ] Chat history loads when returning to a document — AC 9.6
- [ ] SSE streaming displays tokens progressively
- [ ] Enter sends message, Shift+Enter adds newline
- [ ] Send button disabled during streaming (shows spinner)
- [ ] Error messages displayed as assistant messages
- [ ] Auto-scroll to newest content
- [ ] User messages right-aligned, assistant messages left-aligned
- [ ] CitationBlock has proper hover state and click handler

## Files Changed

- `frontend/src/components/workspace/ChatPanel.tsx` — implement from stub
- `frontend/src/components/workspace/CitationBlock.tsx` — implement from stub
- `frontend/src/pages/Workspace.tsx` — wire onCitationClick to DocumentViewer

## Verification

```bash
cd frontend
npm run typecheck
npm run lint
npm run dev
# Manual testing (requires running backend):
# 1. Open workspace with processed document → switch to Chat tab
# 2. Type message → press Enter → user message appears right-aligned
# 3. Tokens stream in left-aligned → response completes with citations
# 4. Click citation → DocumentViewer highlights region
# 5. Send follow-up → context retained
# 6. Navigate away and back → chat history loads
# 7. Type message while streaming → send disabled
```
