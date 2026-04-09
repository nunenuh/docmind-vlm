import { useState } from "react";
import { MessageSquare, Plus, X } from "lucide-react";
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
    <div className="h-full flex flex-col min-w-0">
      {/* Conversation tabs bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-white/[0.05] overflow-x-auto flex-shrink-0 scrollbar-thin">
        {convList.map((conv: ConversationResponse) => (
          <button
            key={conv.id}
            onClick={() => setActiveConvId(conv.id)}
            className={`group flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-md whitespace-nowrap transition-colors ${
              activeConvId === conv.id
                ? "bg-white/[0.06] text-white"
                : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
            }`}
          >
            <MessageSquare className="w-3 h-3 flex-shrink-0" />
            <span className="max-w-[160px] truncate">{conv.title || "Untitled"}</span>
            {/* Delete button on hover */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm("Delete this conversation?")) {
                  deleteConv.mutate(conv.id);
                  if (activeConvId === conv.id) setActiveConvId(null);
                }
              }}
              className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-rose-400 transition-all ml-0.5"
            >
              <X className="w-2.5 h-2.5" />
            </button>
          </button>
        ))}

        {/* New chat button */}
        <button
          onClick={() => setActiveConvId(null)}
          className="p-1.5 text-gray-600 hover:text-indigo-400 hover:bg-indigo-500/[0.06] rounded-md transition-colors ml-1 flex-shrink-0"
          title="New chat"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Chat panel */}
      <div className="flex-1 min-w-0 overflow-hidden">
        <ProjectChatPanel
          projectId={projectId}
          activeConversationId={activeConvId}
          onConversationCreated={setActiveConvId}
        />
      </div>
    </div>
  );
}
