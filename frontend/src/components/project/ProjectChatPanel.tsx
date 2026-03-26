import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { Send, Loader2, User, Bot, FileText, Brain, ChevronDown, ChevronUp, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendProjectChat } from "@/lib/api";
import { fetchConversation } from "@/lib/api";
import { useProjectConversations, useProjectDocuments } from "@/hooks/useProjects";
import type { MessageResponse, ProjectDocumentResponse } from "@/types/api";

interface Citation {
  source_index: number;
  document_id: string;
  page_number: number;
  content_preview: string;
  similarity: number;
}

type DocMap = Map<string, ProjectDocumentResponse>;

interface ProjectChatPanelProps {
  projectId: string;
  activeConversationId: string | null;
  onConversationCreated: (convId: string) => void;
}

export function ProjectChatPanel({ projectId, activeConversationId, onConversationCreated }: ProjectChatPanelProps) {
  const { refetch: refetchConversations } = useProjectConversations(projectId);
  const { data: docs } = useProjectDocuments(projectId);

  // Build a map of document_id → doc for citation resolution
  const docMap: DocMap = useMemo(() => {
    const m = new Map<string, ProjectDocumentResponse>();
    if (docs) {
      for (const d of docs) {
        m.set(d.id, d);
      }
    }
    return m;
  }, [docs]);

  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [thinkingContent, setThinkingContent] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevConvIdRef = useRef<string | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent, thinkingContent, isThinking]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (activeConversationId === prevConvIdRef.current) return;
    prevConvIdRef.current = activeConversationId;

    if (!activeConversationId) {
      setMessages([]);
      setStreamingContent("");
      setThinkingContent("");
      return;
    }

    let cancelled = false;
    setIsLoadingMessages(true);
    fetchConversation(projectId, activeConversationId)
      .then((detail) => {
        if (!cancelled) setMessages(detail.messages);
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      })
      .finally(() => {
        if (!cancelled) setIsLoadingMessages(false);
      });

    return () => { cancelled = true; };
  }, [activeConversationId, projectId]);

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return;

    const message = input.trim();
    setInput("");
    setIsStreaming(true);
    setIsThinking(false);
    setStreamingContent("");
    setThinkingContent("");
    setStatusMessage("Preparing...");
    setStreamingCitations([]);

    const userMsg: MessageResponse = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: message,
      citations: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    let answer = "";
    let thinking = "";
    let citations: Citation[] = [];

    sendProjectChat(
      projectId,
      message,
      activeConversationId,
      (data: unknown) => {
        const event = data as Record<string, unknown>;

        // Capture conversation ID
        if (event.conversation_id) {
          onConversationCreated(event.conversation_id as string);
        }

        const eventType = (event.event || event.type) as string;

        switch (eventType) {
          case "status":
            setStatusMessage((event.message as string) ?? "");
            break;

          case "thinking":
            setIsThinking(true);
            setStatusMessage("");
            thinking += (event.content as string) ?? "";
            setThinkingContent(thinking);
            break;

          case "token":
            setIsThinking(false);
            setStatusMessage("");
            answer += (event.content as string) ?? "";
            setStreamingContent(answer);
            break;

          case "answer":
            if (event.citations) {
              try {
                citations = typeof event.citations === "string"
                  ? JSON.parse(event.citations as string)
                  : (event.citations as Citation[]);
                setStreamingCitations(citations);
              } catch {
                // Ignore
              }
            }
            if (!answer) {
              answer = (event.content as string) ?? "";
              setStreamingContent(answer);
            }
            break;

          case "citations":
            if (event.citations) {
              try {
                citations = typeof event.citations === "string"
                  ? JSON.parse(event.citations as string)
                  : (event.citations as Citation[]);
                setStreamingCitations(citations);
              } catch {
                // Ignore
              }
            }
            break;
        }
      },
      (error: Error) => {
        setIsStreaming(false);
        setIsThinking(false);
        setStatusMessage("");
        setStreamingContent("");
        setThinkingContent("");
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            content: `Error: ${error.message}`,
            citations: null,
            created_at: new Date().toISOString(),
          },
        ]);
      },
      () => {
        // Stream complete — add final message
        setIsStreaming(false);
        setIsThinking(false);
        setStatusMessage("");
        if (answer) {
          setMessages((prev) => [
            ...prev,
            {
              id: `assistant-${Date.now()}`,
              role: "assistant",
              content: answer,
              citations: citations.length > 0 ? JSON.stringify(citations) : null,
              created_at: new Date().toISOString(),
              _thinking: thinking || undefined,
            } as MessageResponse & { _thinking?: string },
          ]);
        }
        setStreamingContent("");
        setThinkingContent("");
        setStreamingCitations([]);
        refetchConversations();
      },
    );
  }, [input, isStreaming, projectId, activeConversationId, onConversationCreated, refetchConversations]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return (
    <div className="flex flex-col h-full bg-[#0a0a0f]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {isLoadingMessages ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
          </div>
        ) : messages.length === 0 && !isStreaming ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4">
              <Bot className="w-7 h-7 text-indigo-400" />
            </div>
            <p className="text-sm text-white font-medium">Ask about your documents</p>
            <p className="text-xs text-gray-500 mt-1 max-w-xs">
              RAG-powered answers with citations from all documents in this project
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                thinking={(msg as MessageResponse & { _thinking?: string })._thinking}
                docMap={docMap}
              />
            ))}
          </>
        )}

        {/* Status indicator */}
        {isStreaming && statusMessage && !isThinking && !streamingContent && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                <span>{statusMessage}</span>
              </div>
            </div>
          </div>
        )}

        {/* Streaming response with thinking */}
        {isStreaming && (isThinking || streamingContent) && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="max-w-[80%] space-y-2">
              {/* Thinking section */}
              {thinkingContent && (
                <ThinkingSection content={thinkingContent} isActive={isThinking} />
              )}

              {/* Answer section */}
              {streamingContent && (
                <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-3">
                  <div className="text-sm text-gray-200 leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0.5">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                  </div>
                  <div className="flex items-center gap-1.5 mt-2">
                    <Loader2 className="w-3 h-3 text-indigo-400 animate-spin" />
                    <span className="text-xs text-gray-500">Generating...</span>
                  </div>
                </div>
              )}

              {/* Streaming citations */}
              {streamingCitations.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {streamingCitations.map((cite) => (
                    <CitationTag key={cite.source_index} citation={cite} docMap={docMap} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#1e1e2e] px-6 py-4 bg-[#0a0a0f]">
        <div className="flex items-end gap-3 max-w-3xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your documents..."
            className="flex-1 bg-[#12121a] border border-[#2a2a3a] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
            rows={1}
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="p-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed rounded-xl text-white transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Thinking Section ──────────────────────────────────── */

function ThinkingSection({ content, isActive }: { content: string; isActive: boolean }) {
  const [isExpanded, setIsExpanded] = useState(true);

  // Auto-collapse when thinking is done
  useEffect(() => {
    if (!isActive && content) {
      const timer = setTimeout(() => setIsExpanded(false), 500);
      return () => clearTimeout(timer);
    }
  }, [isActive, content]);

  return (
    <div className="bg-[#0f0f18] border border-[#1a1a2a] rounded-xl overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:text-gray-300 transition-colors"
      >
        <Brain className={`w-3.5 h-3.5 text-purple-400 ${isActive ? "animate-pulse" : ""}`} />
        <span>{isActive ? "Thinking..." : "Thought process"}</span>
        <span className="ml-auto">
          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </span>
      </button>
      {isExpanded && (
        <div className="px-3 pb-3 max-h-48 overflow-y-auto">
          <p className="text-xs text-gray-500 leading-relaxed whitespace-pre-wrap font-mono">
            {content}
          </p>
        </div>
      )}
    </div>
  );
}

/* ── Citation Tag (clickable with popover) ─────────────── */

function CitationTag({ citation, docMap }: { citation: Citation; docMap: DocMap }) {
  const [showPopover, setShowPopover] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  const doc = docMap.get(citation.document_id);
  const docName = doc?.filename ?? `Document ${citation.source_index}`;
  const isImage = doc && ["png", "jpg", "jpeg", "webp", "tiff"].includes(doc.file_type);

  // Close popover when clicking outside
  useEffect(() => {
    if (!showPopover) return;
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setShowPopover(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showPopover]);

  return (
    <div className="relative" ref={popoverRef}>
      {/* Tag button */}
      <button
        onClick={() => setShowPopover(!showPopover)}
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors ${
          showPopover
            ? "bg-indigo-500/10 border border-indigo-500/30 text-indigo-300"
            : "bg-[#12121a] border border-[#2a2a3a] text-gray-400 hover:text-indigo-400 hover:border-indigo-500/30"
        }`}
      >
        <FileText className="w-3 h-3" />
        <span className="max-w-[120px] truncate">{docName}</span>
        <span className="text-gray-600">p.{citation.page_number}</span>
      </button>

      {/* Popover */}
      {showPopover && (
        <div className="absolute bottom-full left-0 mb-2 w-[320px] bg-[#14161C] border border-white/[0.08] rounded-xl shadow-2xl shadow-black/60 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center gap-2 px-3 py-2.5 border-b border-white/[0.06] bg-white/[0.02]">
            <div className={`w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0 ${
              isImage ? "bg-emerald-500/[0.08]" : "bg-rose-500/[0.08]"
            }`}>
              <FileText className={`w-3 h-3 ${isImage ? "text-emerald-400" : "text-rose-400"}`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[12px] text-gray-200 font-medium truncate">{docName}</p>
              <p className="text-[10px] text-gray-500">
                {doc?.file_type.toUpperCase() ?? "PDF"} · Page {citation.page_number}
                {citation.similarity > 0 && ` · ${Math.round(citation.similarity * 100)}% match`}
              </p>
            </div>
            <button
              onClick={() => setShowPopover(false)}
              className="p-1 text-gray-600 hover:text-gray-300 rounded transition-colors"
            >
              <X className="w-3 h-3" />
            </button>
          </div>

          {/* Content preview */}
          {citation.content_preview && (
            <div className="px-3 py-2.5 max-h-[200px] overflow-y-auto">
              <p className="text-[11px] text-gray-400 leading-relaxed whitespace-pre-wrap">
                {citation.content_preview}
              </p>
            </div>
          )}

          {/* Footer with similarity score */}
          <div className="px-3 py-2 border-t border-white/[0.06] flex items-center gap-2">
            <div className="flex-1 h-1 bg-white/[0.04] rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500/60 rounded-full"
                style={{ width: `${Math.round((citation.similarity || 0) * 100)}%` }}
              />
            </div>
            <span className="text-[10px] text-gray-500 tabular-nums">
              {Math.round((citation.similarity || 0) * 100)}% relevance
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Message Bubble ────────────────────────────────────── */

function MessageBubble({ message, thinking, docMap }: { message: MessageResponse; thinking?: string; docMap: DocMap }) {
  const isUser = message.role === "user";

  const parsedCitations: Citation[] = (() => {
    if (!message.citations) return [];
    try {
      return typeof message.citations === "string"
        ? JSON.parse(message.citations)
        : (message.citations as unknown as Citation[]);
    } catch {
      return [];
    }
  })();

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
        isUser ? "bg-gray-700" : "bg-indigo-500/20"
      }`}>
        {isUser ? <User className="w-4 h-4 text-gray-300" /> : <Bot className="w-4 h-4 text-indigo-400" />}
      </div>
      <div className={`max-w-[80%] space-y-2 ${isUser ? "text-right" : ""}`}>
        {/* Thinking (collapsed by default for saved messages) */}
        {thinking && !isUser && (
          <ThinkingSection content={thinking} isActive={false} />
        )}

        {/* Message content */}
        <div className={`rounded-xl px-4 py-3 ${isUser ? "bg-indigo-600/20 border border-indigo-500/20" : "bg-[#12121a] border border-[#1e1e2e]"}`}>
          {isUser ? (
            <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{message.content}</p>
          ) : (
            <div className="text-sm text-gray-200 leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-li:my-0.5 prose-strong:text-white prose-code:text-indigo-300 prose-code:bg-[#1a1a2a] prose-code:px-1 prose-code:rounded">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {parsedCitations.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {parsedCitations.map((cite) => (
              <CitationTag key={cite.source_index} citation={cite} docMap={docMap} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
