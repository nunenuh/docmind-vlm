import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { FolderOpen, Bot, Settings, Loader2, ChevronRight } from "lucide-react";
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
      <div className="h-full flex items-center justify-center text-gray-500">
        Project not found
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 text-gray-400">
        <FolderOpen className="w-12 h-12 text-gray-600" />
        <p className="text-lg font-medium">Project not found</p>
        <p className="text-sm text-gray-500">It may have been deleted or you don't have access.</p>
        <Link to="/projects" className="text-indigo-400 hover:text-indigo-300 text-sm">
          Back to Projects
        </Link>
      </div>
    );
  }

  const persona = personas?.find((p: PersonaResponse) => p.id === project?.persona_id);

  const handlePersonaChange = (personaId: string | null) => {
    if (!projectId) return;
    updateProject.mutate({ id: projectId, data: { persona_id: personaId ?? undefined } });
  };

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f]">
      {/* Breadcrumb header */}
      <header className="flex items-center justify-between px-4 h-12 border-b border-[#1e1e2e] bg-[#12121a] flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0 text-sm">
          <Link to="/projects" className="text-gray-500 hover:text-gray-300 transition-colors">
            Projects
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
          <FolderOpen className="w-3.5 h-3.5 text-violet-400" />
          <span className="text-white font-medium truncate max-w-[200px]">
            {project?.name ?? "Project"}
          </span>
          {persona && (
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 ml-2">
              <Bot className="w-3 h-3" />
              {persona.name}
            </span>
          )}
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors ${
            showSettings
              ? "bg-white/10 text-white"
              : "text-gray-400 hover:text-white hover:bg-white/5"
          }`}
        >
          <Settings className="w-3.5 h-3.5" />
          Settings
        </button>
      </header>

      {/* Settings panel */}
      {showSettings && (
        <div className="border-b border-[#1e1e2e] bg-[#12121a]/50 px-4 py-3">
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
        <div className="w-[300px] flex-shrink-0 border-r border-[#1e1e2e] bg-[#12121a]/30">
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
