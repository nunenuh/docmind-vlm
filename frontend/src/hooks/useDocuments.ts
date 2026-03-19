import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchDocuments, uploadDocument, deleteDocument } from "@/lib/api";

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
