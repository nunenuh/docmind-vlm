import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";
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
    onSuccess: (data) => {
      toast.success(`Project "${data.name}" created`);
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to create project: ${error.message}`);
    },
  });
}

export function useUpdateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; description?: string; persona_id?: string } }) =>
      updateProject(id, data),
    onSuccess: (_data, variables) => {
      toast.success("Project updated");
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["project", variables.id] });
    },
    onError: (error: Error) => {
      toast.error(`Update failed: ${error.message}`);
    },
  });
}

export function useDeleteProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      toast.success("Project deleted");
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error: Error) => {
      toast.error(`Delete failed: ${error.message}`);
    },
  });
}

export function useProjectDocuments(projectId: string) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["project-documents", projectId],
    queryFn: () => fetchProjectDocuments(projectId),
    enabled: !!projectId,
    // Indexing runs as a background task on the server and there is no push
    // channel yet. While any document is still processing/uploaded we poll
    // so the status dot (and the chunks panel below) reflect reality.
    refetchInterval: (q) => {
      const data = q.state.data as { status?: string }[] | undefined;
      if (!data) return false;
      const hasProcessing = data.some(
        (d) => d.status === "processing" || d.status === "uploaded",
      );
      return hasProcessing ? 3000 : false;
    },
  });

  // When any document transitions from processing/uploaded to ready, the
  // chunks list on the Chunks tab needs to refetch to pick up the new rows.
  const data = query.data;
  useEffect(() => {
    if (!data) return;
    const anyReady = data.some((d) => d.status === "ready");
    if (anyReady) {
      qc.invalidateQueries({ queryKey: ["project-chunks", projectId] });
    }
  }, [data, projectId, qc]);

  return query;
}

export function useAddProjectDocument(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      toast.loading("Uploading & indexing document...", { id: `upload-${projectId}` });
      return addDocumentToProject(projectId, file);
    },
    onSuccess: () => {
      toast.success("Document uploaded and indexed", { id: `upload-${projectId}` });
      qc.invalidateQueries({ queryKey: ["project-documents", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (error: Error) => {
      toast.error(`Upload failed: ${error.message}`, { id: `upload-${projectId}` });
    },
  });
}

export function useRemoveProjectDocument(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => removeProjectDocument(projectId, docId),
    onSuccess: () => {
      toast.success("Document deleted");
      qc.invalidateQueries({ queryKey: ["project-documents", projectId] });
      qc.invalidateQueries({ queryKey: ["project-chunks", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["analytics"] });
    },
    onError: (error: Error) => {
      toast.error(`Delete failed: ${error.message}`);
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
      toast.success("Conversation deleted");
      qc.invalidateQueries({ queryKey: ["project-conversations", projectId] });
    },
    onError: (error: Error) => {
      toast.error(`Delete failed: ${error.message}`);
    },
  });
}
