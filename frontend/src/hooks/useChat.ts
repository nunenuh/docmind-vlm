import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchChatHistory } from "@/lib/api";
import type { ChatHistoryResponse } from "@/types/api";

export function useChatHistory(documentId: string, page = 1, limit = 50) {
  return useQuery<ChatHistoryResponse>({
    queryKey: ["chat-history", documentId, page, limit],
    queryFn: () => fetchChatHistory(documentId, page, limit),
    enabled: !!documentId,
  });
}

export function useInvalidateChatHistory(documentId: string) {
  const queryClient = useQueryClient();
  return () => { queryClient.invalidateQueries({ queryKey: ["chat-history", documentId] }); };
}
