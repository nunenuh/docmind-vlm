import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getEmbeddingStatus, indexDocument } from "@/lib/api";

export function useEmbeddingStatus(documentId: string) {
  return useQuery({
    queryKey: ["embedding-status", documentId],
    queryFn: () => getEmbeddingStatus(documentId),
    enabled: !!documentId,
  });
}

export function useIndexDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => indexDocument(documentId),
    onSuccess: (data) => {
      toast.success(`Indexed ${data.chunks_indexed} chunks`);
      queryClient.invalidateQueries({ queryKey: ["embedding-status", data.document_id] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to index: ${error.message}`);
    },
  });
}
