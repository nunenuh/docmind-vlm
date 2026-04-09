import { useState, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import {
  FolderOpen, Bot, Settings, Loader2, X, FileText, Search, LayoutGrid,
  ArrowLeft, MessageSquare, Info, PanelLeftClose, PanelLeftOpen,
  PanelRightClose, PanelRightOpen,
} from "lucide-react";
import { useProject, useUpdateProject, useProjectDocuments, useProjectConversations } from "@/hooks/useProjects";
import { usePersonas } from "@/hooks/usePersonas";
import { ProjectDocumentsPanel } from "@/components/project/ProjectDocumentsPanel";
import { ProjectChatPanel } from "@/components/project/ProjectChatPanel";
import { ProjectConversationsPanel } from "@/components/project/ProjectConversationsPanel";
import { DocumentViewer } from "@/components/project/DocumentViewer";
import { PersonaSelector } from "@/components/project/PersonaSelector";
import { PersonaEditor } from "@/components/project/PersonaEditor";
import { ChunkBrowser } from "@/components/project/ChunkBrowser";
import type { PersonaResponse, ProjectDocumentResponse } from "@/types/api";

type LeftView = "docs" | "search" | "chunks";
type RightView = "convs" | "info";
type CenterTab = { type: "chat" } | { type: "document"; doc: ProjectDocumentResponse };

const PANEL_MIN = 220;
const PANEL_MAX = 480;
const PANEL_DEFAULT = 280;

export function ProjectWorkspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const { data: project, isLoading } = useProject(projectId ?? "");
  const { data: personas } = usePersonas();
  const { data: docs } = useProjectDocuments(projectId ?? "");
  const { data: conversations } = useProjectConversations(projectId ?? "");
  const updateProject = useUpdateProject();

  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [leftView, setLeftView] = useState<LeftView>("docs");
  const [rightView, setRightView] = useState<RightView>("convs");
  const [leftWidth, setLeftWidth] = useState(PANEL_DEFAULT);
  const [rightWidth, setRightWidth] = useState(PANEL_DEFAULT);
  const [showSettings, setShowSettings] = useState(false);
  const [showPersonaEditor, setShowPersonaEditor] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [centerTabs, setCenterTabs] = useState<CenterTab[]>([{ type: "chat" }]);
  const [activeCenterIdx, setActiveCenterIdx] = useState(0);

  const openDocument = useCallback((doc: ProjectDocumentResponse) => {
    // Check if already open
    const existingIdx = centerTabs.findIndex(
      (t) => t.type === "document" && t.doc.id === doc.id
    );
    if (existingIdx >= 0) {
      setActiveCenterIdx(existingIdx);
      return;
    }
    // Add new tab
    setCenterTabs((prev) => [...prev, { type: "document", doc }]);
    setActiveCenterIdx(centerTabs.length);
  }, [centerTabs]);

  const closeCenterTab = useCallback((idx: number) => {
    if (centerTabs[idx]?.type === "chat") return; // Can't close chat
    setCenterTabs((prev) => prev.filter((_, i) => i !== idx));
    setActiveCenterIdx((prev) => {
      if (prev >= idx && prev > 0) return prev - 1;
      return prev;
    });
  }, [centerTabs]);

  // Resize
  const dragging = useRef<{ side: "left" | "right"; startX: number; startW: number } | null>(null);

  const onMouseDown = useCallback((side: "left" | "right") => (e: React.MouseEvent) => {
    e.preventDefault();
    const startW = side === "left" ? leftWidth : rightWidth;
    dragging.current = { side, startX: e.clientX, startW };

    const onMove = (ev: MouseEvent) => {
      if (!dragging.current) return;
      const dx = ev.clientX - dragging.current.startX;
      const newW = dragging.current.side === "left"
        ? dragging.current.startW + dx
        : dragging.current.startW - dx;
      const clamped = Math.min(PANEL_MAX, Math.max(PANEL_MIN, newW));
      if (dragging.current.side === "left") setLeftWidth(clamped);
      else setRightWidth(clamped);
    };

    const onUp = () => {
      dragging.current = null;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [leftWidth, rightWidth]);

  if (!projectId) {
    return <div className="h-full flex items-center justify-center text-gray-500 bg-[#0B0D11]">Project not found</div>;
  }

  if (isLoading) {
    return (
      <div className="h-full flex flex-col items-center justify-center bg-[#0B0D11] gap-3">
        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
          <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
        </div>
        <p className="text-xs text-gray-500">Loading project...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4 text-gray-400 bg-[#0B0D11]">
        <FolderOpen className="w-8 h-8 text-gray-600" />
        <p className="text-base font-medium text-gray-300">Project not found</p>
        <Link to="/projects" className="flex items-center gap-2 text-sm text-indigo-400 hover:text-indigo-300">
          <ArrowLeft className="w-4 h-4" /> Back to Projects
        </Link>
      </div>
    );
  }

  const persona = personas?.find((p: PersonaResponse) => p.id === project?.persona_id);
  const docCount = docs?.length ?? 0;
  const convCount = conversations?.length ?? 0;

  const handlePersonaChange = (personaId: string | null) => {
    if (!projectId) return;
    updateProject.mutate({ id: projectId, data: { persona_id: personaId ?? undefined } });
  };

  const leftTabs: { key: LeftView; icon: React.ReactNode; label: string; badge?: number }[] = [
    { key: "docs", icon: <FileText className="w-3.5 h-3.5" />, label: "Docs", badge: docCount || undefined },
    { key: "search", icon: <Search className="w-3.5 h-3.5" />, label: "Search" },
    { key: "chunks", icon: <LayoutGrid className="w-3.5 h-3.5" />, label: "Chunks" },
  ];

  const rightTabs: { key: RightView; icon: React.ReactNode; label: string; badge?: number }[] = [
    { key: "convs", icon: <MessageSquare className="w-3.5 h-3.5" />, label: "Chats", badge: convCount || undefined },
    { key: "info", icon: <Info className="w-3.5 h-3.5" />, label: "Info" },
  ];

  return (
    <div className="h-screen flex flex-col bg-[#0B0D11]">
      {/* ── Header ─────────────────────────── */}
      <header className="flex items-center h-[48px] px-4 border-b border-white/[0.05] flex-shrink-0 z-10">
        <div className="flex items-center gap-2.5 min-w-0 flex-1">
          <Link to="/projects" className="p-1.5 text-gray-600 hover:text-gray-300 rounded-md hover:bg-white/[0.04] transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="w-px h-5 bg-white/[0.06]" />
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-violet-500/20 to-indigo-600/20 flex items-center justify-center flex-shrink-0">
            <FolderOpen className="w-3 h-3 text-violet-400" />
          </div>
          <span className="text-[14px] font-semibold text-gray-100 tracking-tight truncate">
            {project?.name ?? "Project"}
          </span>
          {persona && (
            <>
              <div className="w-px h-4 bg-white/[0.06]" />
              <div className="flex items-center gap-1.5 text-[11px] text-indigo-400/70 flex-shrink-0">
                <Bot className="w-3 h-3" />
                <span>{persona.name}</span>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setLeftOpen(!leftOpen)}
            title={leftOpen ? "Hide left panel" : "Show left panel"}
            className={`p-1.5 rounded-md transition-all ${
              leftOpen ? "text-gray-300 bg-white/[0.06]" : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
            }`}
          >
            {leftOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setRightOpen(!rightOpen)}
            title={rightOpen ? "Hide right panel" : "Show right panel"}
            className={`p-1.5 rounded-md transition-all ${
              rightOpen ? "text-gray-300 bg-white/[0.06]" : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
            }`}
          >
            {rightOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
          </button>
          <div className="w-px h-5 bg-white/[0.06] mx-1" />
          <button
            onClick={() => setShowSettings(!showSettings)}
            className={`p-1.5 rounded-md transition-all ${
              showSettings ? "text-gray-300 bg-white/[0.06]" : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* ── Main Area ──────────────────────── */}
      <div className="flex-1 flex overflow-hidden relative">

        {/* ── Left Panel ─────────────────── */}
        {leftOpen && (
          <>
            <div className="flex-shrink-0 bg-[#111318] overflow-hidden flex flex-col" style={{ width: leftWidth }}>
              {/* Tab bar at top */}
              <div className="flex items-center gap-0.5 px-2 pt-2 pb-1 flex-shrink-0 border-b border-white/[0.05]">
                {leftTabs.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setLeftView(tab.key)}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium rounded-md transition-all ${
                      leftView === tab.key
                        ? "text-indigo-400 bg-indigo-500/[0.1]"
                        : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
                    }`}
                  >
                    {tab.icon}
                    <span>{tab.label}</span>
                    {tab.badge && tab.badge > 0 && (
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                        leftView === tab.key
                          ? "bg-indigo-500/20 text-indigo-400"
                          : "bg-white/[0.06] text-gray-600"
                      }`}>
                        {tab.badge > 99 ? "99+" : tab.badge}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Panel content */}
              <div className="flex-1 overflow-hidden">
                <div className="h-full" style={{ width: leftWidth }}>
                  {leftView === "docs" && <ProjectDocumentsPanel projectId={projectId} onDocumentClick={openDocument} />}
                  {leftView === "search" && (
                    <div className="h-full flex flex-col p-4">
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600" />
                        <input
                          type="text"
                          placeholder="Search across documents..."
                          className="w-full pl-9 pr-3 py-2 text-[12px] bg-[#0B0D11] border border-white/[0.06] rounded-lg text-gray-200 placeholder-gray-600 outline-none focus:border-indigo-500/30"
                        />
                      </div>
                      <p className="text-[11px] text-gray-600 mt-4 text-center">Type to search indexed content</p>
                    </div>
                  )}
                  {leftView === "chunks" && (
                    <div className="h-full flex flex-col pt-2">
                      <div className="flex-1 overflow-y-auto px-3">
                        <ChunkBrowser projectId={projectId} />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Resize handle */}
            <div className="w-1 flex-shrink-0 cursor-col-resize relative z-[8] group" onMouseDown={onMouseDown("left")}>
              <div className="absolute inset-y-0 left-0 w-px bg-white/[0.05] group-hover:w-[3px] group-hover:bg-indigo-500 group-hover:rounded transition-all" />
            </div>
          </>
        )}

        {/* ── Center Area (tabbed) ────────── */}
        <div className="flex-1 min-w-0 flex flex-col">
          {/* Center tab bar — only show if more than 1 tab */}
          {centerTabs.length > 1 && (
            <div className="flex items-center gap-0.5 px-2 pt-1.5 pb-1 border-b border-white/[0.05] flex-shrink-0 bg-[#0B0D11] overflow-x-auto">
              {centerTabs.map((tab, idx) => (
                <button
                  key={tab.type === "chat" ? "chat" : tab.doc.id}
                  onClick={() => setActiveCenterIdx(idx)}
                  className={`group flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium rounded-md whitespace-nowrap transition-all ${
                    activeCenterIdx === idx
                      ? "text-gray-200 bg-white/[0.06]"
                      : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
                  }`}
                >
                  {tab.type === "chat" ? (
                    <>
                      <MessageSquare className="w-3 h-3 text-indigo-400" />
                      <span>Chat</span>
                    </>
                  ) : (
                    <>
                      <FileText className="w-3 h-3 text-rose-400" />
                      <span className="max-w-[120px] truncate">{tab.doc.filename}</span>
                      {/* Close button */}
                      <button
                        onClick={(e) => { e.stopPropagation(); closeCenterTab(idx); }}
                        className="opacity-0 group-hover:opacity-100 p-0.5 text-gray-600 hover:text-gray-300 transition-all ml-0.5"
                      >
                        <X className="w-2.5 h-2.5" />
                      </button>
                    </>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Active tab content */}
          <div className="flex-1 min-w-0 overflow-hidden">
            {centerTabs[activeCenterIdx]?.type === "chat" ? (
              <ProjectChatPanel
                projectId={projectId}
                activeConversationId={activeConvId}
                onConversationCreated={setActiveConvId}
              />
            ) : centerTabs[activeCenterIdx]?.type === "document" ? (
              <DocumentViewer
                documentId={centerTabs[activeCenterIdx].doc.id}
                filename={centerTabs[activeCenterIdx].doc.filename}
                fileType={centerTabs[activeCenterIdx].doc.file_type}
              />
            ) : null}
          </div>
        </div>

        {/* ── Right Panel ────────────────── */}
        {rightOpen && (
          <>
            {/* Resize handle */}
            <div className="w-1 flex-shrink-0 cursor-col-resize relative z-[8] group" onMouseDown={onMouseDown("right")}>
              <div className="absolute inset-y-0 right-0 w-px bg-white/[0.05] group-hover:w-[3px] group-hover:bg-indigo-500 group-hover:rounded transition-all" />
            </div>

            <div className="flex-shrink-0 bg-[#111318] overflow-hidden flex flex-col" style={{ width: rightWidth }}>
              {/* Tab bar at top */}
              <div className="flex items-center gap-0.5 px-2 pt-2 pb-1 flex-shrink-0 border-b border-white/[0.05]">
                {rightTabs.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setRightView(tab.key)}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 text-[11px] font-medium rounded-md transition-all ${
                      rightView === tab.key
                        ? "text-indigo-400 bg-indigo-500/[0.1]"
                        : "text-gray-600 hover:text-gray-400 hover:bg-white/[0.03]"
                    }`}
                  >
                    {tab.icon}
                    <span>{tab.label}</span>
                    {tab.badge && tab.badge > 0 && (
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                        rightView === tab.key
                          ? "bg-indigo-500/20 text-indigo-400"
                          : "bg-white/[0.06] text-gray-600"
                      }`}>
                        {tab.badge > 99 ? "99+" : tab.badge}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Panel content */}
              <div className="flex-1 overflow-hidden">
                <div className="h-full" style={{ width: rightWidth }}>
                  {rightView === "convs" && (
                    <ProjectConversationsPanel
                      projectId={projectId}
                      activeConversationId={activeConvId}
                      onSelect={setActiveConvId}
                    />
                  )}
                  {rightView === "info" && (
                    <div className="h-full flex flex-col">
                      <div className="flex-1 overflow-y-auto px-4 pt-3 space-y-4">
                        <SettingsGroup label="Name">
                          <p className="text-[13px] text-gray-200">{project?.name}</p>
                        </SettingsGroup>
                        {project?.description && (
                          <SettingsGroup label="Description">
                            <p className="text-[12px] text-gray-400 leading-relaxed">{project.description}</p>
                          </SettingsGroup>
                        )}
                        <SettingsGroup label="AI Persona">
                          <PersonaSelector
                            value={project?.persona_id ?? null}
                            onChange={handlePersonaChange}
                            onCreateNew={() => setShowPersonaEditor(true)}
                          />
                        </SettingsGroup>
                        <SettingsGroup label="Stats">
                          <div className="space-y-1.5 text-[12px]">
                            <div className="flex justify-between text-gray-400">
                              <span>Documents</span><span className="text-gray-200">{docCount}</span>
                            </div>
                            <div className="flex justify-between text-gray-400">
                              <span>Conversations</span><span className="text-gray-200">{convCount}</span>
                            </div>
                          </div>
                        </SettingsGroup>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {/* ── Settings Slide-over ────────── */}
        {showSettings && (
          <>
            <div className="absolute inset-0 bg-black/40 backdrop-blur-sm z-20" onClick={() => setShowSettings(false)} />
            <div className="absolute right-0 top-0 bottom-0 w-[340px] bg-[#111318]/95 backdrop-blur-xl border-l border-white/[0.06] z-30 shadow-2xl shadow-black/50 flex flex-col">
              <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06]">
                <h3 className="text-sm font-semibold text-gray-100">Project Settings</h3>
                <button onClick={() => setShowSettings(false)} className="p-1.5 text-gray-500 hover:text-white transition-colors rounded-lg hover:bg-white/[0.06]">
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

      {showPersonaEditor && (
        <PersonaEditor
          onClose={() => setShowPersonaEditor(false)}
          onSaved={(newPersona) => handlePersonaChange(newPersona.id)}
        />
      )}
    </div>
  );
}

/* ── Sub-components ──────────────────────── */

function SettingsGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-2">{label}</label>
      {children}
    </div>
  );
}
