import { useState } from "react";
import { Loader2, FolderOpen, Plus, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useProjects, useCreateProject, useDeleteProject } from "@/hooks/useProjects";
import { usePersonas } from "@/hooks/usePersonas";
import { ProjectCard } from "@/components/project/ProjectCard";
import { PersonaSelector } from "@/components/project/PersonaSelector";
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

  const personaMap = new Map(
    (personas ?? []).map((p: PersonaResponse) => [p.id, p.name]),
  );

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
          onClick={() => setShowNewModal(true)}
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
            onClick={() => setShowNewModal(true)}
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
          <div className="relative bg-[#12121a] border border-[#1e1e2e] rounded-xl w-full max-w-md mx-4 shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-[#1e1e2e]">
              <h2 className="text-lg font-semibold text-white">New Project</h2>
              <button
                onClick={() => setShowNewModal(false)}
                className="p-1 text-gray-400 hover:text-white transition-colors rounded-md hover:bg-white/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Name *</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Q4 Financial Reports"
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  autoFocus
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">Description</label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="What is this project about?"
                  rows={2}
                  className="w-full bg-[#0a0a0f] border border-[#2a2a3a] rounded-lg px-3 py-2.5 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1.5">AI Persona</label>
                <PersonaSelector
                  value={newPersonaId}
                  onChange={setNewPersonaId}
                  onCreateNew={() => setShowPersonaEditor(true)}
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
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
                  className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
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
