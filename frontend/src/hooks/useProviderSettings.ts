import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  getProviders,
  setProvider,
  deleteProvider,
  testProvider,
} from "@/lib/api";
import type { ProviderType, SetProviderRequest, ValidateProviderRequest } from "@/types/provider";

export function useProviders() {
  return useQuery({
    queryKey: ["providers"],
    queryFn: getProviders,
  });
}

export function useSetProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ type, data }: { type: ProviderType; data: SetProviderRequest }) =>
      setProvider(type, data),
    onSuccess: () => {
      toast.success("Provider saved");
      queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to save provider: ${error.message}`);
    },
  });
}

export function useDeleteProvider() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (type: ProviderType) => deleteProvider(type),
    onSuccess: () => {
      toast.success("Provider removed");
      queryClient.invalidateQueries({ queryKey: ["providers"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to remove provider: ${error.message}`);
    },
  });
}

export function useTestProvider() {
  return useMutation({
    mutationFn: (data: ValidateProviderRequest) => testProvider(data),
  });
}
