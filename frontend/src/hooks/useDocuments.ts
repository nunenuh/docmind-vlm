import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { fetchDocuments, fetchDocument, fetchDocumentUrl, uploadDocument, deleteDocument } from "@/lib/api";

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
    queryFn: () => fetchDocumentUrl(documentId),
    enabled: !!documentId,
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
