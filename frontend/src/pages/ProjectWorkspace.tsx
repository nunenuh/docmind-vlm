import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  FolderOpen, Bot, Settings, Loader2, X, FileText,
  ArrowLeft, PanelLeftClose, PanelLeftOpen,
} from "lucide-react";
import { useProject, useUpdateProject, useProjectDocuments } from "@/hooks/useProjects";
import { usePersonas } from "@/hooks/usePersonas";
import { ProjectDocumentsPanel } from "@/components/project/ProjectDocumentsPanel";
import { ProjectChatTab } from "@/components/project/ProjectChatTab";
import { PersonaSelector } from "@/components/project/PersonaSelector";
import { PersonaEditor } from "@/components/project/PersonaEditor";
import { ChunkBrowser } from "@/components/project/ChunkBrowser";
import type { PersonaResponse } from "@/types/api";

export function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading } = useProject(projectId ?? "");
  const { data: personas } = usePersonas();
  const { data: docs } = useProjectDocuments(projectId ?? "");
  const updateProject = useUpdateProject();

  const [showDocs, setShowDocs] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [showPersonaEditor, setShowPersonaEditor] = useState(false);

  if (!projectId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 bg-[#0B0D11]">
        Project not found
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-[#0B0D11] gap-3">
        <div className="relative">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
          </div>
          <div className="absolute inset-0 rounded-xl bg-indigo-500/5 animate-ping" />
        </div>
        <p className="text-xs text-gray-500 tracking-wide">Loading project...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 text-gray-400 bg-[#0B0D11]">
        <div className="w-16 h-16 rounded-2xl bg-gray-800/50 border border-gray-700/50 flex items-center justify-center">
          <FolderOpen className="w-8 h-8 text-gray-600" />
        </div>
        <p className="text-base font-medium text-gray-300">Project not found</p>
        <p className="text-sm text-gray-500">It may have been deleted or you don't have access.</p>
        <Link
          to="/projects"
          className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300 transition-colors mt-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </Link>
      </div>
    );
  }

  const persona = personas?.find((p: PersonaResponse) => p.id === project?.persona_id);
  const docCount = docs?.length ?? 0;

  const handlePersonaChange = (personaId: string | null) => {
    if (!projectId) return;
    updateProject.mutate({ id: projectId, data: { persona_id: personaId ?? undefined } });
  };

  return (
    <div className="h-screen flex flex-col bg-[#0B0D11]">
      {/* ── Header ─────────────────────────────────────── */}
      <header className="flex items-center h-[52px] px-4 border-b border-white/[0.05] flex-shrink-0 z-10">
        {/* Left: back + project info */}
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <Link
            to="/projects"
            className="p-1.5 text-gray-600 hover:text-gray-300 rounded-md hover:bg-white/[0.04] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div className="w-px h-5 bg-white/[0.05] mx-1" />

          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500/20 to-indigo-600/20 flex items-center justify-center flex-shrink-0">
            <FolderOpen className="w-3 h-3 text-violet-400" />
          </div>
          <span className="text-[13px] font-semibold text-gray-100 tracking-tight truncate max-w-[220px]">
            {project?.name ?? "Project"}
          </span>

          {/* Persona badge */}
          {persona && (
            <>
              <div className="w-px h-4 bg-white/[0.05] mx-2" />
              <div className="flex items-center gap-1.5 text-[11px] text-indigo-400/80">
                <Bot className="w-3 h-3" />
                <span className="tracking-wide">{persona.name}</span>
              </div>
            </>
          )}
        </div>

        {/* Right: docs toggle + settings */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowDocs(!showDocs)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium rounded-md transition-all ${
              showDocs
                ? "text-gray-300 bg-white/[0.06]"
                : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
            }`}
          >
            {showDocs ? <PanelLeftClose className="w-3.5 h-3.5" /> : <PanelLeftOpen className="w-3.5 h-3.5" />}
            <FileText className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Docs</span>
            {docCount > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.06] text-gray-500">{docCount}</span>
            )}
          </button>

          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-1.5 rounded-md transition-all ${
              showSettings
                ? "text-gray-300 bg-white/[0.06]"
                : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* ── Content ────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Documents panel (collapsible) */}
        <div
          className={`flex-shrink-0 border-r border-white/[0.05] transition-all duration-300 overflow-hidden ${
            showDocs ? "w-[300px]" : "w-0 border-r-0"
          }`}
        >
          <div className="w-[300px] h-full">
            <ProjectDocumentsPanel projectId={projectId} />
          </div>
        </div>

        {/* Chat area */}
        <div className="flex-1 min-w-0">
          <ProjectChatTab projectId={projectId} />
        </div>

        {/* ── Settings slide-over ──────────────────────── */}
        {showSettings && (
          <>
            <div
              className="absolute inset-0 bg-black/40 backdrop-blur-sm z-20 transition-opacity"
              onClick={() => setShowSettings(false)}
            />
            <div className="absolute right-0 top-0 bottom-0 w-[340px] bg-[#111318]/95 backdrop-blur-xl border-l border-white/[0.06] z-30 shadow-2xl shadow-black/50 flex flex-col">
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
                <h3 className="text-sm font-semibold text-gray-100 tracking-tight">Project Settings</h3>
                <button
                  onClick={() => setShowSettings(false)}
                  className="p-1.5 text-gray-500 hover:text-white transition-colors rounded-lg hover:bg-white/[0.06]"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="p-5 space-y-5 flex-1 overflow-y-auto">
                <SettingsGroup label="Project Name">
                  <p className="text-sm text-gray-200">{project?.name}</p>
                </SettingsGroup>

                {project?.description && (
                  <SettingsGroup label="Description">
                    <p className="text-sm text-gray-400 leading-relaxed">{project.description}</p>
                  </SettingsGroup>
                )}

                <SettingsGroup label="AI Persona">
                  <PersonaSelector
                    value={project?.persona_id ?? null}
                    onChange={handlePersonaChange}
                    onCreateNew={() => setShowPersonaEditor(true)}
                  />
                </SettingsGroup>

                <SettingsGroup label="Indexed Chunks">
                  <ChunkBrowser projectId={projectId} />
                </SettingsGroup>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Persona Editor Modal */}
      {showPersonaEditor && (
        <PersonaEditor
          onClose={() => setShowPersonaEditor(false)}
          onSaved={(newPersona) => handlePersonaChange(newPersona.id)}
        />
      )}
    </div>
  );
}

/* ── Sub-components ───────────────────────────────────── */

function SettingsGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2">
        {label}
      </label>
      {children}
    </div>
  );
}
