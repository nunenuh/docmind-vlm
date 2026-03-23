# Streaming + Thinking — DashScope SSE

## Overview

Enable real-time streaming of LLM responses with visible thinking/reasoning process.
Qwen3-VL-Plus supports `enable_thinking` which returns `reasoning_content` (chain-of-thought)
followed by `content` (final answer), both streamed token-by-token via SSE.

## DashScope Streaming API

### Request

```
POST https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
Headers:
  Authorization: Bearer {api_key}
  Content-Type: application/json
  X-DashScope-SSE: enable        ← enables SSE streaming

Body:
{
  "model": "qwen3-vl-plus",
  "input": {"messages": [...]},
  "parameters": {
    "max_tokens": 4096,
    "temperature": 0.1,
    "result_format": "message",
    "enable_thinking": true,       ← enables reasoning output
    "incremental_output": true     ← token-by-token (not cumulative)
  }
}
```

### Response (SSE stream)

```
Phase 1 — Thinking tokens:
  data: {"output":{"choices":[{"message":{"content":[],"reasoning_content":"Let me"}}]}}
  data: {"output":{"choices":[{"message":{"content":[],"reasoning_content":" analyze"}}]}}
  ...

Phase 2 — Answer tokens:
  data: {"output":{"choices":[{"message":{"content":"Based on","reasoning_content":""}}]}}
  data: {"output":{"choices":[{"message":{"content":" the document","reasoning_content":""}}]}}
  ...

Phase 3 — Done:
  data: {"output":{"choices":[{"finish_reason":"stop","message":{"content":"","reasoning_content":""}}]}}
```

Key fields:
- `reasoning_content` — non-empty during thinking phase
- `content` — non-empty during answer phase (can be string or list)
- `finish_reason` — `"null"` during streaming, `"stop"` when done
- `usage.output_tokens_details.reasoning_tokens` — thinking token count
- `usage.output_tokens_details.text_tokens` — answer token count

## Architecture

```
Frontend                    Backend SSE                  DashScope SSE
┌──────────┐              ┌──────────────┐              ┌──────────────┐
│ Chat UI  │◄─── SSE ────│ Chat Handler │◄─── SSE ────│ Qwen3-VL-Plus│
│          │              │              │              │              │
│ thinking │◄── thinking ─│ reason_node  │◄─ reasoning ─│ reasoning_   │
│ (collap) │   tokens     │              │   _content   │ content      │
│          │              │              │              │              │
│ answer   │◄── token ────│              │◄─ content ───│ content      │
│ (stream) │   tokens     │              │   tokens     │              │
│          │              │              │              │              │
│ sources  │◄── citations─│ cite_node    │              │              │
└──────────┘              └──────────────┘              └──────────────┘
```

## Backend Changes

### 1. DashScope Provider — New Streaming Method

**File**: `backend/src/docmind/library/providers/dashscope.py`

```python
async def chat_stream(
    self,
    images: list[np.ndarray],
    message: str,
    history: list[dict],
    system_prompt: str,
    enable_thinking: bool = True,
) -> AsyncGenerator[dict, None]:
    """Stream chat response with optional thinking.

    Yields dicts:
      {"type": "thinking", "content": "token..."}
      {"type": "answer", "content": "token..."}
      {"type": "done", "usage": {...}}
    """
```

Implementation:
- Build messages same as `chat()`
- Add headers: `X-DashScope-SSE: enable`
- Add parameters: `enable_thinking: true`, `incremental_output: true`
- Use `httpx.AsyncClient.stream("POST", ...)` to read SSE events
- Parse each `data:` line, extract `reasoning_content` vs `content`
- Yield `{"type": "thinking", "content": token}` for reasoning tokens
- Yield `{"type": "answer", "content": token}` for answer tokens
- Yield `{"type": "done", "usage": usage_dict}` on `finish_reason: "stop"`

### 2. Config — New Settings

**File**: `backend/src/docmind/core/config.py`

```python
# Streaming
ENABLE_THINKING: bool = Field(default=True)
THINKING_BUDGET: int = Field(default=10000)  # max thinking tokens
```

### 3. Project Chat Pipeline — Streaming Reason Node

**File**: `backend/src/docmind/library/pipeline/rag.py`

The `reason_node` currently calls `provider.chat()` (non-streaming) and returns the full answer.
Change to use `provider.chat_stream()` and yield events through an asyncio queue:

```python
async def reason_node_streaming(
    state: dict,
    event_queue: asyncio.Queue,
) -> dict:
    """Stream thinking + answer tokens via event_queue."""
    provider = get_vlm_provider()

    async for event in provider.chat_stream(
        images=state["page_images"],
        message=full_message,
        history=history,
        system_prompt=system_prompt,
        enable_thinking=get_settings().ENABLE_THINKING,
    ):
        await event_queue.put(event)

    return {"answer": accumulated_answer, "reasoning": accumulated_thinking}
```

### 4. Project Chat Handler — SSE Events

**File**: `backend/src/docmind/modules/projects/apiv1/handler.py`

Current SSE events:
```
event: answer     data: {"content": "full answer"}
event: citations  data: {"citations": [...]}
event: done       data: {}
```

New SSE events:
```
event: thinking   data: {"content": "token"}     ← reasoning tokens
event: token      data: {"content": "token"}     ← answer tokens
event: answer     data: {"content": "full text"}  ← complete answer (for history)
event: citations  data: {"citations": [...]}
event: done       data: {"conversation_id": "...", "usage": {...}}
```

## Frontend Changes

### 1. ProjectChatPanel — Thinking UI

**File**: `frontend/src/components/project/ProjectChatPanel.tsx`

New state:
```typescript
const [thinkingContent, setThinkingContent] = useState("");
const [isThinking, setIsThinking] = useState(false);
```

Event handling:
```typescript
if (event.type === "thinking") {
  setIsThinking(true);
  thinkingContent += event.content;
  setThinkingContent(thinkingContent);
} else if (event.type === "token") {
  setIsThinking(false);  // switch from thinking to answering
  answer += event.content;
  setStreamingContent(answer);
}
```

### 2. Thinking Display

Collapsible section above the answer:

```
┌──────────────────────────────────────┐
│ 🧠 Thinking...                    ▼ │
│ ┌──────────────────────────────────┐ │
│ │ Let me analyze the resume...     │ │
│ │ The document mentions Machine    │ │
│ │ Learning Engineer at PT Tiga...  │ │
│ └──────────────────────────────────┘ │
│                                      │
│ Based on the resume, this person     │
│ has dual expertise in **Full Stack   │
│ Web Development** and **Machine      │
│ Learning Engineering**...            │
└──────────────────────────────────────┘
```

- While thinking: show animated "Thinking..." with expanding text
- After thinking ends: collapse by default, click to expand
- Thinking text rendered in smaller, muted font
- Answer text rendered in normal font with Markdown

### 3. Thinking Section Component

```typescript
function ThinkingSection({ content, isActive }: { content: string; isActive: boolean }) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Auto-collapse when thinking is done
  useEffect(() => {
    if (!isActive && content) setIsExpanded(false);
  }, [isActive]);

  return (
    <div className="mb-2">
      <button onClick={() => setIsExpanded(!isExpanded)}>
        {isActive ? "🧠 Thinking..." : "🧠 Thought process"}
        {isExpanded ? "▲" : "▼"}
      </button>
      {isExpanded && (
        <div className="text-xs text-gray-500 bg-gray-900/50 rounded p-2 mt-1 max-h-40 overflow-y-auto">
          {content}
        </div>
      )}
    </div>
  );
}
```

## Data Model

No DB changes needed. Thinking content is transient (streaming only, not stored in messages).

## Settings

| Key | Default | Description |
|-----|---------|-------------|
| `ENABLE_THINKING` | `true` | Enable reasoning output from Qwen |
| `THINKING_BUDGET` | `10000` | Max tokens for thinking phase |

## Implementation Order

1. Add `chat_stream()` to DashScope provider
2. Add config settings
3. Update project chat handler to use streaming SSE
4. Update `reason_node` to support streaming
5. Update frontend `ProjectChatPanel` with thinking UI
6. Tests: mock streaming responses

## Rules

- Thinking tokens are **not stored** in the database (transient)
- Answer tokens **are stored** as the final message content
- If `ENABLE_THINKING=false`, skip thinking and stream answer directly
- Thinking phase should have a visual indicator (animated brain icon)
- Thinking auto-collapses when answer starts
- Stored messages should only contain the final answer, not thinking
- Per-document chat (non-project) can also use streaming but thinking is optional
