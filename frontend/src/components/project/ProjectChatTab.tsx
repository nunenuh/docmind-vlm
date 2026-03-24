import { useState } from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { useProjectConversations, useDeleteConversation } from "@/hooks/useProjects";
import { ProjectChatPanel } from "./ProjectChatPanel";
import type { ConversationResponse } from "@/types/api";

interface Props {
  projectId: string;
}

export function ProjectChatTab({ projectId }: Props) {
  const { data: conversations } = useProjectConversations(projectId);
  const deleteConv = useDeleteConversation(projectId);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);

  const convList = conversations ?? [];

  return (
    <div className="h-full flex bg-[#0a0a0f]">
      {/* Conversation sidebar */}
      <div className="w-64 flex-shrink-0 border-r border-[#1e1e2e] flex flex-col">
        <div className="px-4 py-3 border-b border-[#1e1e2e]">
          <button
            onClick={() => setActiveConvId(null)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {convList.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center px-4">
              <MessageSquare className="w-6 h-6 text-gray-700 mb-2" />
              <p className="text-xs text-gray-500">No conversations yet</p>
            </div>
          ) : (
            <div className="space-y-0.5 px-2">
              {convList.map((conv: ConversationResponse) => (
                <div
                  key={conv.id}
                  onClick={() => setActiveConvId(conv.id)}
                  className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                    activeConvId === conv.id
                      ? "bg-indigo-500/15 text-white"
                      : "text-gray-400 hover:bg-white/5 hover:text-gray-300"
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5 flex-shrink-0" />
                  <span className="text-xs truncate flex-1">{conv.title}</span>
                  {conv.message_count !== undefined && (
                    <span className="text-[10px] text-gray-600">{conv.message_count}</span>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm("Delete this conversation?")) {
                        deleteConv.mutate(conv.id);
                        if (activeConvId === conv.id) setActiveConvId(null);
                      }
                    }}
                    className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-rose-400 transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat panel */}
      <div className="flex-1 min-w-0">
        <ProjectChatPanel
          projectId={projectId}
          activeConversationId={activeConvId}
          onConversationCreated={setActiveConvId}
        />
      </div>
    </div>
  );
}
