import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchProjects,
  fetchProject,
  createProject,
  updateProject,
  deleteProject,
  fetchProjectDocuments,
  removeProjectDocument,
  addDocumentToProject,
  fetchProjectConversations,
  deleteConversation,
} from "@/lib/api";

export function useProjects(page = 1, limit = 20) {
  return useQuery({
    queryKey: ["projects", page, limit],
    queryFn: () => fetchProjects(page, limit),
  });
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ["project", id],
    queryFn: () => fetchProject(id),
    enabled: !!id,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; description?: string; persona_id?: string } }) =>
      updateProject(id, data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["project", variables.id] });
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useProjectDocuments(projectId: string) {
  return useQuery({
    queryKey: ["project-documents", projectId],
    queryFn: () => fetchProjectDocuments(projectId),
    enabled: !!projectId,
  });
}

export function useAddProjectDocument(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => addDocumentToProject(projectId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project-documents", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useRemoveProjectDocument(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => removeProjectDocument(projectId, docId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project-documents", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
}

export function useProjectConversations(projectId: string) {
  return useQuery({
    queryKey: ["project-conversations", projectId],
    queryFn: () => fetchProjectConversations(projectId),
    enabled: !!projectId,
  });
}

export function useDeleteConversation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (convId: string) => deleteConversation(projectId, convId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project-conversations", projectId] });
    },
  });
}
