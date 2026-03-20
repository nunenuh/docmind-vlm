import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, User, Bot } from "lucide-react";
import { useChatHistory, useInvalidateChatHistory } from "@/hooks/useChat";
import { sendChatMessage } from "@/lib/api";
import { CitationBlock } from "./CitationBlock";
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
  const [streamingContent, setStreamingContent] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const messages = history?.items ?? [];

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return;

    const message = input.trim();
    setInput("");
    setIsStreaming(true);
    setStreamingContent("");

    sendChatMessage(
      documentId,
      message,
      (data: unknown) => {
        const event = data as Record<string, unknown>;
        if (event.type === "token") {
          setStreamingContent((prev) => prev + (event.content ?? ""));
        } else if (event.type === "error") {
          setStreamingContent(String(event.message ?? "An error occurred"));
        } else if (event.type === "done") {
          // Pipeline complete — history will refresh
        }
      },
      (error: Error) => {
        setIsStreaming(false);
        setStreamingContent(`Error: ${error.message}`);
        setTimeout(() => setStreamingContent(""), 5000);
      },
      () => {
        setIsStreaming(false);
        setStreamingContent("");
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
          <div className="flex flex-col items-center justify-center py-16 px-6">
            <div className="w-12 h-12 rounded-xl bg-gray-900 border border-gray-800 flex items-center justify-center mb-4">
              <Bot className="w-6 h-6 text-gray-700" />
            </div>
            <p className="text-sm font-medium text-gray-400 mb-1">Chat with this document</p>
            <p className="text-xs text-gray-600 text-center">Ask questions and get answers with source citations.</p>
          </div>
        )}

        {messages.map((msg: ChatMessageResponse) => (
          <MessageBubble key={msg.id} message={msg} onCitationClick={selectField} />
        ))}

        {isStreaming && streamingContent && (
          <div className="flex gap-3">
            <div className="w-7 h-7 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-blue-400" />
            </div>
            <div className="bg-gray-900 rounded-lg px-4 py-3 max-w-[85%]">
              <p className="text-sm text-gray-200 whitespace-pre-wrap">{streamingContent}</p>
              <Loader2 className="w-3 h-3 text-blue-400 animate-spin mt-2" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 px-4 py-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this document..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all duration-200"
            rows={1}
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="p-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg text-white transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  onCitationClick,
}: {
  message: ChatMessageResponse;
  onCitationClick: (fieldId: string | null) => void;
}) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
        isUser ? "bg-gray-700" : "bg-blue-500/20"
      }`}>
        {isUser ? <User className="w-4 h-4 text-gray-300" /> : <Bot className="w-4 h-4 text-blue-400" />}
      </div>
      <div className={`max-w-[85%] ${isUser ? "text-right" : ""}`}>
        <div className={`rounded-lg px-4 py-3 ${isUser ? "bg-blue-600/20" : "bg-gray-900"}`}>
          <p className="text-sm text-gray-200 whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.citations.map((c, i) => (
              <CitationBlock key={i} citation={c} onClick={() => onCitationClick(null)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
