import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, User, Bot, FileText, Brain, ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendProjectChat } from "@/lib/api";
import { fetchConversation } from "@/lib/api";
import { useProjectConversations } from "@/hooks/useProjects";
import type { MessageResponse } from "@/types/api";

interface Citation {
  source_index: number;
  document_id: string;
  page_number: number;
  content_preview: string;
  similarity: number;
}

interface ProjectChatPanelProps {
  projectId: string;
  activeConversationId: string | null;
  onConversationCreated: (convId: string) => void;
}

export function ProjectChatPanel({ projectId, activeConversationId, onConversationCreated }: ProjectChatPanelProps) {
  const { refetch: refetchConversations } = useProjectConversations(projectId);

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
            // Final complete answer — don't update streamingContent
            // as it's already built from tokens. Parse citations.
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
            // If we didn't get token events, use the answer content
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
              // Store thinking for this message
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
                    <CitationTag key={cite.source_index} citation={cite} />
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

function CitationTag({ citation }: { citation: Citation }) {
  return (
    <div
      className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#12121a] border border-[#2a2a3a] rounded text-xs text-gray-400 hover:text-indigo-400 hover:border-indigo-500/30 transition-colors cursor-default"
      title={citation.content_preview}
    >
      <FileText className="w-3 h-3" />
      <span>Source {citation.source_index}</span>
      <span className="text-gray-600">p.{citation.page_number}</span>
    </div>
  );
}

function MessageBubble({ message, thinking }: { message: MessageResponse; thinking?: string }) {
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
              <CitationTag key={cite.source_index} citation={cite} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
