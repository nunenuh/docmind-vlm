import { useState } from "react";
import { Loader2, FolderOpen, Plus, X, Bot, Check } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useProjects, useCreateProject, useDeleteProject } from "@/hooks/useProjects";
import { usePersonas } from "@/hooks/usePersonas";
import { ProjectCard } from "@/components/project/ProjectCard";
import { PersonaEditor } from "@/components/project/PersonaEditor";
import type { PersonaResponse } from "@/types/api";

export function ProjectDashboard() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const limit = 20;

  const { data, isLoading } = useProjects(page, limit);
  const { data: personas } = usePersonas();
  const createProj = useCreateProject();
  const deleteProj = useDeleteProject();

  const [showNewModal, setShowNewModal] = useState(false);
  const [showPersonaEditor, setShowPersonaEditor] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newPersonaId, setNewPersonaId] = useState<string | null>(null);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    createProj.mutate(
      {
        name: newName.trim(),
        description: newDescription.trim() || undefined,
        persona_id: newPersonaId ?? undefined,
      },
      {
        onSuccess: (project) => {
          setShowNewModal(false);
          setNewName("");
          setNewDescription("");
          setNewPersonaId(null);
          navigate(`/projects/${project.id}`);
        },
      },
    );
  };

  const handleDelete = (id: string) => {
    deleteProj.mutate(id);
  };

  const openNewModal = () => {
    setNewName("");
    setNewDescription("");
    setNewPersonaId(null);
    setShowNewModal(true);
  };

  const personaMap = new Map(
    (personas ?? []).map((p: PersonaResponse) => [p.id, p.name]),
  );

  const presetPersonas = (personas ?? []).filter((p: PersonaResponse) => p.is_preset);
  const customPersonas = (personas ?? []).filter((p: PersonaResponse) => !p.is_preset);

  const projects = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-white">Projects</h1>
          <p className="text-sm text-gray-400 mt-1">
            Create projects, upload documents, and chat with AI
          </p>
        </div>
        <button
          onClick={openNewModal}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Project
        </button>
      </div>

      {/* Project grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
        </div>
      ) : projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24">
          <div className="w-20 h-20 rounded-2xl bg-[#12121a] border border-[#1e1e2e] flex items-center justify-center mb-5">
            <FolderOpen className="w-10 h-10 text-gray-700" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">No projects yet</h3>
          <p className="text-gray-500 text-sm mb-6">Create one to get started.</p>
          <button
            onClick={openNewModal}
            className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create your first project
          </button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-400">
              {total} project{total !== 1 ? "s" : ""}
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                personaName={project.persona_id ? personaMap.get(project.persona_id) ?? null : null}
                onDelete={handleDelete}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-10">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all"
              >
                Previous
              </button>
              <span className="text-sm text-gray-500">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* New Project Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowNewModal(false)} />
          <div className="relative bg-[#12121a] border border-[#1e1e2e] rounded-2xl w-full max-w-lg mx-4 shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e1e2e]">
              <div>
                <h2 className="text-lg font-semibold text-white">Create New Project</h2>
                <p className="text-xs text-gray-500 mt-0.5">Set up a document workspace with AI</p>
              </div>
              <button
                onClick={() => setShowNewModal(false)}
                className="p-1.5 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-6 space-y-5">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Project Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g., Customer Support Docs"
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  autoFocus
                  required
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">
                  Description <span className="text-gray-600 font-normal">(optional)</span>
                </label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="What kind of documents will this project contain?"
                  rows={2}
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              {/* Persona selection */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  AI Persona <span className="text-gray-600 font-normal">(optional)</span>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {/* No persona option */}
                  <button
                    type="button"
                    onClick={() => setNewPersonaId(null)}
                    className={`relative flex items-center gap-2 px-3 py-2.5 rounded-xl text-left text-sm transition-all border ${
                      newPersonaId === null
                        ? "border-indigo-500 bg-indigo-500/10 text-white"
                        : "border-[#2a2a3a] bg-[#0a0a0f] text-gray-400 hover:border-[#3a3a4a] hover:text-gray-300"
                    }`}
                  >
                    <X className="w-4 h-4 flex-shrink-0" />
                    <span>No persona</span>
                    {newPersonaId === null && (
                      <Check className="w-3.5 h-3.5 text-indigo-400 ml-auto" />
                    )}
                  </button>

                  {/* Preset personas */}
                  {presetPersonas.map((p: PersonaResponse) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setNewPersonaId(p.id)}
                      className={`relative flex items-center gap-2 px-3 py-2.5 rounded-xl text-left text-sm transition-all border ${
                        newPersonaId === p.id
                          ? "border-indigo-500 bg-indigo-500/10 text-white"
                          : "border-[#2a2a3a] bg-[#0a0a0f] text-gray-400 hover:border-[#3a3a4a] hover:text-gray-300"
                      }`}
                    >
                      <Bot className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{p.name}</span>
                      {newPersonaId === p.id && (
                        <Check className="w-3.5 h-3.5 text-indigo-400 ml-auto flex-shrink-0" />
                      )}
                    </button>
                  ))}

                  {/* Custom personas */}
                  {customPersonas.map((p: PersonaResponse) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => setNewPersonaId(p.id)}
                      className={`relative flex items-center gap-2 px-3 py-2.5 rounded-xl text-left text-sm transition-all border ${
                        newPersonaId === p.id
                          ? "border-indigo-500 bg-indigo-500/10 text-white"
                          : "border-[#2a2a3a] bg-[#0a0a0f] text-gray-400 hover:border-[#3a3a4a] hover:text-gray-300"
                      }`}
                    >
                      <Bot className="w-4 h-4 flex-shrink-0" />
                      <span className="truncate">{p.name}</span>
                      {newPersonaId === p.id && (
                        <Check className="w-3.5 h-3.5 text-indigo-400 ml-auto flex-shrink-0" />
                      )}
                    </button>
                  ))}
                </div>

                {/* Create custom persona link */}
                <button
                  type="button"
                  onClick={() => setShowPersonaEditor(true)}
                  className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  + Create custom persona
                </button>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-1 border-t border-[#1e1e2e]">
                <button
                  type="button"
                  onClick={() => setShowNewModal(false)}
                  className="px-4 py-2.5 text-sm text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createProj.isPending || !newName.trim()}
                  className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl transition-colors"
                >
                  {createProj.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  Create Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Persona Editor Modal */}
      {showPersonaEditor && (
        <PersonaEditor
          onClose={() => setShowPersonaEditor(false)}
          onSaved={(persona) => setNewPersonaId(persona.id)}
        />
      )}
    </div>
  );
}
