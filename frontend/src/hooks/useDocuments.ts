import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchDocuments, createDocument, deleteDocument } from "@/lib/api";
import type { DocumentCreate } from "@/types/api";

export function useDocuments(page = 1, limit = 20) {
  return useQuery({ queryKey: ["documents", page, limit], queryFn: () => fetchDocuments(page, limit) });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DocumentCreate) => createDocument(data),
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
