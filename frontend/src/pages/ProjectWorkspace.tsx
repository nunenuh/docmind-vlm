import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  FolderOpen, Bot, Settings, Loader2, ChevronRight, X,
  FileText, MessageSquare, Database, Zap, ArrowLeft,
} from "lucide-react";
import { useProject, useUpdateProject, useProjectDocuments } from "@/hooks/useProjects";
import { usePersonas } from "@/hooks/usePersonas";
import { ProjectDocumentsTab } from "@/components/project/ProjectDocumentsTab";
import { ProjectChatTab } from "@/components/project/ProjectChatTab";
import { PersonaSelector } from "@/components/project/PersonaSelector";
import { PersonaEditor } from "@/components/project/PersonaEditor";
import { ChunkBrowser } from "@/components/project/ChunkBrowser";
import type { PersonaResponse } from "@/types/api";

type TabId = "documents" | "chat";

export function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading } = useProject(projectId ?? "");
  const { data: personas } = usePersonas();
  const { data: docs } = useProjectDocuments(projectId ?? "");
  const updateProject = useUpdateProject();

  const [activeTab, setActiveTab] = useState<TabId>("chat");
  const [showSettings, setShowSettings] = useState(false);
  const [showPersonaEditor, setShowPersonaEditor] = useState(false);

  if (!projectId) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 bg-[#0C0D12]">
        Project not found
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-[#0C0D12] gap-3">
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
      <div className="h-full flex flex-col items-center justify-center gap-4 text-gray-400 bg-[#0C0D12]">
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
    <div className="h-screen flex flex-col bg-[#0C0D12]">
      {/* ── Header ────────────────────────────────────────── */}
      <header className="flex items-center h-14 px-5 border-b border-white/[0.06] bg-[#0C0D12]/80 backdrop-blur-xl flex-shrink-0 z-10">
        {/* Left: breadcrumb + project info */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <Link
            to="/projects"
            className="flex items-center gap-1 text-gray-500 hover:text-gray-300 transition-colors text-xs tracking-wide uppercase"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Projects</span>
          </Link>

          <div className="w-px h-4 bg-white/[0.06]" />

          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 border border-violet-500/10 flex items-center justify-center flex-shrink-0">
              <FolderOpen className="w-3.5 h-3.5 text-violet-400" />
            </div>
            <div className="min-w-0">
              <h1 className="text-[13px] font-semibold text-gray-100 truncate max-w-[220px] tracking-tight">
                {project?.name ?? "Project"}
              </h1>
            </div>
          </div>

          {/* Persona badge */}
          {persona && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/[0.08] border border-indigo-500/[0.12] ml-1">
              <Bot className="w-3 h-3 text-indigo-400" />
              <span className="text-[11px] font-medium text-indigo-300 tracking-wide">
                {persona.name}
              </span>
            </div>
          )}
        </div>

        {/* Center: tab switcher */}
        <div className="flex items-center bg-white/[0.03] rounded-lg p-0.5 border border-white/[0.04]">
          <TabButton
            active={activeTab === "documents"}
            onClick={() => setActiveTab("documents")}
            icon={<FileText className="w-3.5 h-3.5" />}
            label="Documents"
            count={docCount}
          />
          <TabButton
            active={activeTab === "chat"}
            onClick={() => setActiveTab("chat")}
            icon={<MessageSquare className="w-3.5 h-3.5" />}
            label="Chat"
          />
        </div>

        {/* Right: settings */}
        <div className="flex items-center gap-2 flex-1 justify-end">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`flex items-center gap-1.5 text-[11px] font-medium px-3 py-1.5 rounded-lg transition-all duration-200 ${
              showSettings
                ? "bg-white/[0.08] text-white border border-white/[0.08]"
                : "text-gray-500 hover:text-gray-300 hover:bg-white/[0.04] border border-transparent"
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Settings</span>
          </button>
        </div>
      </header>

      {/* ── Tab content ───────────────────────────────────── */}
      <div className="flex-1 overflow-hidden relative">
        <div className={`absolute inset-0 transition-opacity duration-300 ${activeTab === "documents" ? "opacity-100 z-10" : "opacity-0 z-0 pointer-events-none"}`}>
          <ProjectDocumentsTab projectId={projectId} />
        </div>
        <div className={`absolute inset-0 transition-opacity duration-300 ${activeTab === "chat" ? "opacity-100 z-10" : "opacity-0 z-0 pointer-events-none"}`}>
          <ProjectChatTab projectId={projectId} />
        </div>

        {/* ── Settings slide-over ───────────────────────── */}
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
                {/* Project info */}
                <SettingsGroup label="Project Name">
                  <p className="text-sm text-gray-200">{project?.name}</p>
                </SettingsGroup>

                {project?.description && (
                  <SettingsGroup label="Description">
                    <p className="text-sm text-gray-400 leading-relaxed">{project.description}</p>
                  </SettingsGroup>
                )}

                {/* Persona */}
                <SettingsGroup label="AI Persona">
                  <PersonaSelector
                    value={project?.persona_id ?? null}
                    onChange={handlePersonaChange}
                    onCreateNew={() => setShowPersonaEditor(true)}
                  />
                </SettingsGroup>

                {/* Stats */}
                <SettingsGroup label="Knowledge Base">
                  <div className="grid grid-cols-2 gap-2">
                    <StatMini icon={<FileText className="w-3.5 h-3.5" />} label="Documents" value={docCount} />
                    <StatMini icon={<Database className="w-3.5 h-3.5" />} label="RAG Chunks" value="—" />
                  </div>
                </SettingsGroup>

                {/* Chunks */}
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

function TabButton({
  active,
  onClick,
  icon,
  label,
  count,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`relative flex items-center gap-1.5 px-3.5 py-1.5 text-[12px] font-medium rounded-md transition-all duration-200 ${
        active
          ? "bg-white/[0.08] text-white shadow-sm shadow-black/20"
          : "text-gray-500 hover:text-gray-300"
      }`}
    >
      <span className={active ? "text-indigo-400" : ""}>{icon}</span>
      {label}
      {count !== undefined && count > 0 && (
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ml-0.5 ${
          active ? "bg-indigo-500/20 text-indigo-300" : "bg-white/[0.06] text-gray-500"
        }`}>
          {count}
        </span>
      )}
    </button>
  );
}

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

function StatMini({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-white/[0.02] rounded-lg border border-white/[0.04]">
      <span className="text-gray-500">{icon}</span>
      <div>
        <p className="text-xs font-semibold text-gray-200">{value}</p>
        <p className="text-[10px] text-gray-500">{label}</p>
      </div>
    </div>
  );
}
