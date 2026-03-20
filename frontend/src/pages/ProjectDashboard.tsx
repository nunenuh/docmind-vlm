import { useState } from "react";
import { FileText, LogOut, Loader2, FolderOpen, Plus, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { signOut } from "@/lib/supabase";
import { useAuthStore } from "@/stores/auth-store";
import { useProjects, useCreateProject, useDeleteProject } from "@/hooks/useProjects";
import { usePersonas } from "@/hooks/usePersonas";
import { ProjectCard } from "@/components/project/ProjectCard";
import { PersonaSelector } from "@/components/project/PersonaSelector";
import { PersonaEditor } from "@/components/project/PersonaEditor";
import type { PersonaResponse } from "@/types/api";

export function ProjectDashboard() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
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

  const handleLogout = async () => {
    await signOut();
    navigate("/");
  };

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
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-white font-bold">
            <FileText className="w-5 h-5 text-blue-400" />
            DocMind-VLM
          </Link>
          <div className="flex items-center gap-6">
            <nav className="flex items-center gap-4">
              <Link
                to="/dashboard"
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Documents
              </Link>
              <Link
                to="/projects"
                className="text-sm text-white font-medium"
              >
                Projects
              </Link>
            </nav>
            <div className="flex items-center gap-4">
              {user && (
                <span className="text-sm text-gray-400 hidden sm:block">
                  {user.email}
                </span>
              )}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Sign out
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white mb-2">Knowledge Base</h1>
            <p className="text-gray-400">Create projects, upload documents, and chat with AI</p>
          </div>
          <button
            onClick={() => setShowNewModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Project
          </button>
        </div>

        {/* Project grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-20">
            <FolderOpen className="w-16 h-16 text-gray-700 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No projects yet</h3>
            <p className="text-gray-500 mb-6">Create one to get started.</p>
            <button
              onClick={() => setShowNewModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create your first project
            </button>
          </div>
        ) : (
          <>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
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
              <div className="flex items-center justify-center gap-2 mt-8">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1.5 text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-500">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </main>

      {/* New Project Modal */}
      {showNewModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowNewModal(false)} />
          <div className="relative bg-gray-900 border border-gray-800 rounded-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-800">
              <h2 className="text-lg font-semibold text-white">New Project</h2>
              <button
                onClick={() => setShowNewModal(false)}
                className="p-1 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Name *</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. Q4 Financial Reports"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                  autoFocus
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
                <textarea
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="What is this project about?"
                  rows={2}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">AI Persona</label>
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
                  className="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createProj.isPending || !newName.trim()}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
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
