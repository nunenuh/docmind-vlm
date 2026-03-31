import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { fetchDocuments, fetchDocument, uploadDocument, deleteDocument } from "@/lib/api";
import { useAuthStore } from "@/stores/auth-store";

export function useDocument(documentId: string) {
  return useQuery({
    queryKey: ["document", documentId],
    queryFn: () => fetchDocument(documentId),
    enabled: !!documentId,
  });
}

export function useDocumentUrl(documentId: string) {
  return useQuery({
    queryKey: ["document-url", documentId],
    queryFn: async () => {
      const token = useAuthStore.getState().accessToken;
      const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8009";
      const resp = await fetch(`${BASE_URL}/api/v1/documents/${documentId}/file`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!resp.ok) throw new Error("Failed to load document");
      const blob = await resp.blob();
      return { url: URL.createObjectURL(blob) };
    },
    enabled: !!documentId,
    staleTime: 5 * 60_000,
  });
}

export function useDocuments(page = 1, limit = 20, standalone = true) {
  return useQuery({
    queryKey: ["documents", page, limit, standalone],
    queryFn: () => fetchDocuments(page, limit, standalone),
  });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      toast.loading("Uploading document...", { id: "upload" });
      return uploadDocument(file);
    },
    onSuccess: (data) => {
      toast.success(`"${data.filename}" uploaded successfully`, { id: "upload" });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error: Error) => {
      toast.error(`Upload failed: ${error.message}`, { id: "upload" });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      toast.success("Document deleted");
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error: Error) => {
      toast.error(`Delete failed: ${error.message}`);
    },
  });
}
