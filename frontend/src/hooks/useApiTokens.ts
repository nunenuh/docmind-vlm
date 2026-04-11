import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { listTokens, createToken, updateToken, revokeToken, regenerateToken } from "@/lib/api";
import type { CreateTokenRequest, UpdateTokenRequest } from "@/types/api-token";

export function useTokens() {
  return useQuery({
    queryKey: ["api-tokens"],
    queryFn: listTokens,
  });
}

export function useCreateToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateTokenRequest) => createToken(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-tokens"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to create token: ${error.message}`);
    },
  });
}

export function useUpdateToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTokenRequest }) =>
      updateToken(id, data),
    onSuccess: () => {
      toast.success("API key updated");
      queryClient.invalidateQueries({ queryKey: ["api-tokens"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to update token: ${error.message}`);
    },
  });
}

export function useRegenerateToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => regenerateToken(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-tokens"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to regenerate token: ${error.message}`);
    },
  });
}

export function useRevokeToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => revokeToken(id),
    onSuccess: () => {
      toast.success("API key revoked");
      queryClient.invalidateQueries({ queryKey: ["api-tokens"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to revoke token: ${error.message}`);
    },
  });
}
