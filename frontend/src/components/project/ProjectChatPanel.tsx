import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Loader2, User, Bot, Plus, Trash2, MessageSquare } from "lucide-react";
import { sendProjectChat } from "@/lib/api";
import { useProjectConversations, useDeleteConversation } from "@/hooks/useProjects";
import type { ConversationResponse, MessageResponse } from "@/types/api";
import { fetchConversation } from "@/lib/api";

interface ProjectChatPanelProps {
  projectId: string;
}

export function ProjectChatPanel({ projectId }: ProjectChatPanelProps) {
  const { data: conversations, refetch: refetchConversations } = useProjectConversations(projectId);
  const deleteConv = useDeleteConversation(projectId);

  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  const loadConversation = useCallback(async (convId: string) => {
    setActiveConvId(convId);
    setIsLoadingMessages(true);
    try {
      const detail = await fetchConversation(projectId, convId);
      setMessages(detail.messages);
    } catch {
      setMessages([]);
    } finally {
      setIsLoadingMessages(false);
    }
  }, [projectId]);

  const handleNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    setStreamingContent("");
  };

  const handleDeleteConversation = (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    deleteConv.mutate(convId, {
      onSuccess: () => {
        if (activeConvId === convId) {
          handleNewChat();
        }
      },
    });
  };

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return;

    const message = input.trim();
    setInput("");
    setIsStreaming(true);
    setStreamingContent("");

    // Optimistically add user message
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
      activeConvId,
      (data: unknown) => {
        const event = data as Record<string, unknown>;
        // Handle different event types from RAG pipeline
        if (event.event === "answer" || event.type === "answer") {
          answer = (event.content as string) ?? "";
          setStreamingContent(answer);
        } else if (event.event === "token" || event.type === "token") {
          answer += (event.content as string) ?? "";
          setStreamingContent(answer);
        }
        // Capture conversation ID
        if (event.conversation_id) {
          setActiveConvId(event.conversation_id as string);
        }
      },
      (error: Error) => {
        setIsStreaming(false);
        setStreamingContent("");
        // Show error as assistant message
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
        // Add the accumulated answer as assistant message
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
  }, [input, isStreaming, projectId, activeConvId, refetchConversations]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const convList = conversations ?? [];

  return (
    <div className="flex h-full">
      {/* Conversation sidebar */}
      <div className="w-52 flex-shrink-0 border-r border-gray-800 flex flex-col">
        <div className="p-3 border-b border-gray-800">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Chat
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {convList.length === 0 ? (
            <div className="text-center py-8 px-3">
              <MessageSquare className="w-6 h-6 text-gray-700 mx-auto mb-2" />
              <p className="text-xs text-gray-600">No conversations yet</p>
            </div>
          ) : (
            <div className="py-1">
              {convList.map((conv: ConversationResponse) => (
                <div
                  key={conv.id}
                  onClick={() => loadConversation(conv.id)}
                  role="button"
                  tabIndex={0}
                  className={`group w-full text-left px-3 py-2 text-xs transition-colors flex items-start gap-2 cursor-pointer ${
                    activeConvId === conv.id
                      ? "bg-gray-800/80 text-white"
                      : "text-gray-400 hover:bg-gray-800/40 hover:text-gray-300"
                  }`}
                >
                  <MessageSquare className="w-3 h-3 mt-0.5 flex-shrink-0" />
                  <span className="flex-1 truncate">{conv.title ?? "Untitled"}</span>
                  <button
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-red-400 transition-all"
                    aria-label="Delete conversation"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {isLoadingMessages ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
            </div>
          ) : messages.length === 0 && !isStreaming ? (
            <div className="text-center py-12 text-gray-500">
              <Bot className="w-10 h-10 mx-auto mb-3 text-gray-700" />
              <p className="text-sm">Ask a question about your documents</p>
              <p className="text-xs text-gray-600 mt-1">RAG-powered answers with citations</p>
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
              placeholder="Ask about your documents..."
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
    </div>
  );
}

function MessageBubble({ message }: { message: MessageResponse }) {
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
        {message.citations && (
          <div className="mt-1.5 text-xs text-gray-500 italic">
            {message.citations}
          </div>
        )}
      </div>
    </div>
  );
}
