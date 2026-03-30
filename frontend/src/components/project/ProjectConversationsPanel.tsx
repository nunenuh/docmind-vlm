import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { useProjectConversations, useDeleteConversation } from "@/hooks/useProjects";
import type { ConversationResponse } from "@/types/api";

interface Props {
  projectId: string;
  activeConversationId: string | null;
  onSelect: (convId: string | null) => void;
}

export function ProjectConversationsPanel({ projectId, activeConversationId, onSelect }: Props) {
  const { data: conversations } = useProjectConversations(projectId);
  const deleteConv = useDeleteConversation(projectId);
  const convList = conversations ?? [];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-3.5 pb-2 flex-shrink-0">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">
          Conversations
        </span>
      </div>

      {/* New chat */}
      <div className="px-2 pb-2 flex-shrink-0">
        <button
          onClick={() => onSelect(null)}
          className="w-full flex items-center justify-center gap-1.5 py-2 border border-dashed border-white/[0.08] rounded-lg text-[11px] font-medium text-gray-500 hover:text-indigo-400 hover:border-indigo-500/30 hover:bg-indigo-500/[0.04] transition-all"
        >
          <Plus className="w-3.5 h-3.5" />
          New Chat
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {convList.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <MessageSquare className="w-8 h-8 text-gray-700 mb-2" />
            <p className="text-[11px] text-gray-600">No conversations yet</p>
            <p className="text-[10px] text-gray-700 mt-0.5">Start chatting to create one</p>
          </div>
        ) : (
          <div className="space-y-0.5">
            {convList.map((conv: ConversationResponse) => (
              <button
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                className={`group w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all ${
                  activeConversationId === conv.id
                    ? "bg-white/[0.06] text-white"
                    : "text-gray-400 hover:text-gray-200 hover:bg-white/[0.03]"
                }`}
              >
                <div className={`w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 ${
                  activeConversationId === conv.id
                    ? "bg-indigo-500/15"
                    : "bg-white/[0.04]"
                }`}>
                  <MessageSquare className={`w-3.5 h-3.5 ${
                    activeConversationId === conv.id ? "text-indigo-400" : "text-gray-600"
                  }`} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] font-medium truncate">
                    {conv.title || "Untitled"}
                  </div>
                  <div className="text-[10px] text-gray-600 mt-0.5">
                    {conv.message_count ?? 0} messages
                  </div>
                </div>
                {/* Delete */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm("Delete this conversation?")) {
                      deleteConv.mutate(conv.id);
                      if (activeConversationId === conv.id) onSelect(null);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 text-gray-600 hover:text-rose-400 rounded transition-all flex-shrink-0"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
