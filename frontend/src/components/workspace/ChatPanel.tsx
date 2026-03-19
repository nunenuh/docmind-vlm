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
        }
      },
      () => {
        setIsStreaming(false);
        setStreamingContent("");
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
          <div className="text-center py-12 text-gray-500">
            <Bot className="w-10 h-10 mx-auto mb-3 text-gray-700" />
            <p>Ask a question about this document</p>
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
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
            rows={1}
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="p-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg text-white transition-colors"
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
