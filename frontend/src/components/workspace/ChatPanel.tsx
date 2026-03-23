import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, User, Bot, Brain, ChevronDown, ChevronUp } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useChatHistory, useInvalidateChatHistory } from "@/hooks/useChat";
import { sendChatMessage } from "@/lib/api";
import { useWorkspaceStore } from "@/stores/workspace-store";
import type { ChatMessageResponse } from "@/types/api";

interface ChatPanelProps {
  documentId: string;
}

export function ChatPanel({ documentId }: ChatPanelProps) {
  const { data: history } = useChatHistory(documentId);
  const invalidateHistory = useInvalidateChatHistory(documentId);
  const selectField = useWorkspaceStore((s) => s.selectField);

  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [thinkingContent, setThinkingContent] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const messages = history?.items ?? [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent, thinkingContent, isThinking]);

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return;

    const message = input.trim();
    setInput("");
    setIsStreaming(true);
    setIsThinking(false);
    setStreamingContent("");
    setThinkingContent("");
    setStatusMessage("Preparing...");

    let answer = "";
    let thinking = "";

    sendChatMessage(
      documentId,
      message,
      (data: unknown) => {
        const event = data as Record<string, unknown>;
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
            if (!answer) {
              answer = (event.content as string) ?? "";
              setStreamingContent(answer);
            }
            break;
          case "error":
            setStreamingContent(String(event.message ?? "An error occurred"));
            break;
        }
      },
      (error: Error) => {
        setIsStreaming(false);
        setIsThinking(false);
        setStatusMessage("");
        setStreamingContent(`Error: ${error.message}`);
      },
      () => {
        setIsStreaming(false);
        setIsThinking(false);
        setStatusMessage("");
        setStreamingContent("");
        setThinkingContent("");
        invalidateHistory();
      },
    );
  }, [input, isStreaming, documentId, invalidateHistory]);

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
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && !isStreaming && (
          <div className="flex flex-col items-center justify-center py-12 px-6">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-indigo-400" />
            </div>
            <p className="text-sm font-medium text-gray-300 mb-1">Chat with this document</p>
            <p className="text-xs text-gray-500 text-center max-w-xs">
              Ask questions about the extracted data. Process the document first for best results.
            </p>
          </div>
        )}

        {messages.map((msg: ChatMessageResponse) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Status */}
        {isStreaming && statusMessage && !isThinking && !streamingContent && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-lg px-3 py-2">
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <Loader2 className="w-3 h-3 text-indigo-400 animate-spin" />
                <span>{statusMessage}</span>
              </div>
            </div>
          </div>
        )}

        {/* Streaming response */}
        {isStreaming && (isThinking || streamingContent) && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="max-w-[85%] space-y-2">
              {thinkingContent && (
                <ThinkingBlock content={thinkingContent} isActive={isThinking} />
              )}
              {streamingContent && (
                <div className="bg-[#12121a] border border-[#1e1e2e] rounded-lg px-3 py-2.5">
                  <div className="text-sm text-gray-200 leading-relaxed prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{streamingContent}</ReactMarkdown>
                  </div>
                  <Loader2 className="w-3 h-3 text-indigo-400 animate-spin mt-2" />
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#1e1e2e] px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this document..."
            className="flex-1 bg-[#12121a] border border-[#2a2a3a] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
            rows={1}
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="p-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg text-white transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function ThinkingBlock({ content, isActive }: { content: string; isActive: boolean }) {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!isActive) {
      const t = setTimeout(() => setExpanded(false), 500);
      return () => clearTimeout(t);
    }
  }, [isActive]);

  return (
    <div className={`bg-[#0f0f18] border border-[#1a1a2a] rounded-lg overflow-hidden ${expanded ? "" : "inline-block"}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-2.5 py-1.5 text-xs text-gray-400 hover:text-gray-300"
      >
        <Brain className={`w-3.5 h-3.5 text-purple-400 ${isActive ? "animate-pulse" : ""}`} />
        <span>{isActive ? "Thinking..." : "Thought process"}</span>
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
      </button>
      {expanded && (
        <div className="px-2.5 pb-2.5 max-h-32 overflow-y-auto">
          <p className="text-xs text-gray-500 leading-relaxed whitespace-pre-wrap font-mono">{content}</p>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessageResponse }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
        isUser ? "bg-gray-700" : "bg-indigo-500/20"
      }`}>
        {isUser ? <User className="w-4 h-4 text-gray-300" /> : <Bot className="w-4 h-4 text-indigo-400" />}
      </div>
      <div className={`max-w-[85%] ${isUser ? "text-right" : ""}`}>
        <div className={`rounded-lg px-3 py-2.5 ${isUser ? "bg-indigo-600/20 border border-indigo-500/20" : "bg-[#12121a] border border-[#1e1e2e]"}`}>
          {isUser ? (
            <p className="text-sm text-gray-200 whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="text-sm text-gray-200 leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
