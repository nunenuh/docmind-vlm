import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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

export function useDocuments(page = 1, limit = 20) {
  return useQuery({ queryKey: ["documents", page, limit], queryFn: () => fetchDocuments(page, limit) });
}

export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["documents"] }); },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["documents"] }); },
  });
}
