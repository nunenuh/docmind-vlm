import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, User, Bot } from "lucide-react";
import { sendProjectChat } from "@/lib/api";
import { fetchConversation } from "@/lib/api";
import { useProjectConversations } from "@/hooks/useProjects";
import type { MessageResponse } from "@/types/api";

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
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevConvIdRef = useRef<string | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  // Load messages when active conversation changes
  useEffect(() => {
    if (activeConversationId === prevConvIdRef.current) return;
    prevConvIdRef.current = activeConversationId;

    if (!activeConversationId) {
      setMessages([]);
      setStreamingContent("");
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
    setStreamingContent("");

    const userMsg: MessageResponse = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: message,
      citations: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    let answer = "";

    sendProjectChat(
      projectId,
      message,
      activeConversationId,
      (data: unknown) => {
        const event = data as Record<string, unknown>;
        if (event.event === "answer" || event.type === "answer") {
          answer = (event.content as string) ?? "";
          setStreamingContent(answer);
        } else if (event.event === "token" || event.type === "token") {
          answer += (event.content as string) ?? "";
          setStreamingContent(answer);
        }
        if (event.conversation_id) {
          onConversationCreated(event.conversation_id as string);
        }
      },
      (error: Error) => {
        setIsStreaming(false);
        setStreamingContent("");
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
        setIsStreaming(false);
        if (answer) {
          setMessages((prev) => [
            ...prev,
            {
              id: `assistant-${Date.now()}`,
              role: "assistant",
              content: answer,
              citations: null,
              created_at: new Date().toISOString(),
            },
          ]);
        }
        setStreamingContent("");
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
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </>
        )}

        {isStreaming && streamingContent && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-3 max-w-[80%]">
              <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{streamingContent}</p>
              <Loader2 className="w-3 h-3 text-indigo-400 animate-spin mt-2" />
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

function MessageBubble({ message }: { message: MessageResponse }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
        isUser ? "bg-gray-700" : "bg-indigo-500/20"
      }`}>
        {isUser ? <User className="w-4 h-4 text-gray-300" /> : <Bot className="w-4 h-4 text-indigo-400" />}
      </div>
      <div className={`max-w-[80%] ${isUser ? "text-right" : ""}`}>
        <div className={`rounded-xl px-4 py-3 ${isUser ? "bg-indigo-600/20 border border-indigo-500/20" : "bg-[#12121a] border border-[#1e1e2e]"}`}>
          <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{message.content}</p>
        </div>
        {message.citations && (
          <div className="mt-1.5 text-xs text-gray-500 italic">
            {message.citations}
          </div>
        )}
      </div>
    </div>
  );
}
