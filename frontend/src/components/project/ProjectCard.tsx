import { useNavigate } from "react-router-dom";
import { FolderOpen, Trash2, FileText, Bot } from "lucide-react";
import type { ProjectResponse } from "@/types/api";

function formatTimeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

interface ProjectCardProps {
  project: ProjectResponse;
  personaName?: string | null;
  onDelete: (id: string) => void;
}

export function ProjectCard({ project, personaName, onDelete }: ProjectCardProps) {
  const navigate = useNavigate();

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm(`Delete project "${project.name}"? This cannot be undone.`)) {
      onDelete(project.id);
    }
  };

  return (
    <div
      onClick={() => navigate(`/projects/${project.id}`)}
      className="group bg-gray-900/50 border border-gray-800 rounded-xl p-5 cursor-pointer hover:border-blue-500/30 transition-colors"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
            <FolderOpen className="w-5 h-5 text-purple-400" />
          </div>
          <div className="min-w-0">
            <h3 className="text-white font-medium truncate">{project.name}</h3>
            {project.description && (
              <p className="text-sm text-gray-500 truncate">{project.description}</p>
            )}
          </div>
        </div>
        <button
          onClick={handleDelete}
          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-all"
          aria-label="Delete project"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-gray-800 text-gray-300">
          <FileText className="w-3 h-3" />
          {project.document_count} {project.document_count === 1 ? "doc" : "docs"}
        </span>
        {personaName && (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full bg-blue-900/50 text-blue-300">
            <Bot className="w-3 h-3" />
            {personaName}
          </span>
        )}
        <span className="text-xs text-gray-600 ml-auto">
          Updated {formatTimeAgo(project.updated_at)}
        </span>
      </div>
    </div>
  );
}
