import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, FolderOpen, Bot, Settings, Loader2 } from "lucide-react";
import { useProject, useUpdateProject } from "@/hooks/useProjects";
import { usePersonas } from "@/hooks/usePersonas";
import { ProjectDocumentList } from "@/components/project/ProjectDocumentList";
import { ProjectChatPanel } from "@/components/project/ProjectChatPanel";
import { PersonaSelector } from "@/components/project/PersonaSelector";
import { PersonaEditor } from "@/components/project/PersonaEditor";
import type { PersonaResponse } from "@/types/api";

export function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading } = useProject(projectId ?? "");
  const { data: personas } = usePersonas();
  const updateProject = useUpdateProject();

  const [showSettings, setShowSettings] = useState(false);
  const [showPersonaEditor, setShowPersonaEditor] = useState(false);

  if (!projectId) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500">
        Project not found
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
      </div>
    );
  }

  const persona = personas?.find((p: PersonaResponse) => p.id === project?.persona_id);

  const handlePersonaChange = (personaId: string | null) => {
    if (!projectId) return;
    updateProject.mutate({ id: projectId, data: { persona_id: personaId ?? undefined } });
  };

  return (
    <div className="h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-4 h-12 border-b border-gray-800 bg-gray-900/50 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link to="/projects" className="text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <FolderOpen className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-white font-medium truncate max-w-[200px]">
            {project?.name ?? "Project"}
          </span>
          {persona && (
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-blue-900/50 text-blue-300">
              <Bot className="w-3 h-3" />
              {persona.name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-colors ${
              showSettings
                ? "bg-gray-800 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
            Settings
          </button>
        </div>
      </header>

      {/* Settings panel (collapsible) */}
      {showSettings && (
        <div className="border-b border-gray-800 bg-gray-900/30 px-4 py-3">
          <div className="max-w-sm">
            <label className="block text-xs font-medium text-gray-400 mb-1.5">AI Persona</label>
            <PersonaSelector
              value={project?.persona_id ?? null}
              onChange={handlePersonaChange}
              onCreateNew={() => setShowPersonaEditor(true)}
            />
          </div>
        </div>
      )}

      {/* Split layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Document list */}
        <div className="w-[320px] flex-shrink-0 border-r border-gray-800">
          <ProjectDocumentList projectId={projectId} />
        </div>

        {/* Right: Chat panel */}
        <div className="flex-1 min-w-0">
          <ProjectChatPanel projectId={projectId} />
        </div>
      </div>

      {/* Persona Editor Modal */}
      {showPersonaEditor && (
        <PersonaEditor
          onClose={() => setShowPersonaEditor(false)}
          onSaved={(newPersona) => {
            handlePersonaChange(newPersona.id);
          }}
        />
      )}
    </div>
  );
}
