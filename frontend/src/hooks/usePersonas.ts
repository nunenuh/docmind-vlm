import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchPersonas,
  createPersona,
  updatePersona,
  deletePersona,
} from "@/lib/api";

export function usePersonas() {
  return useQuery({
    queryKey: ["personas"],
    queryFn: fetchPersonas,
  });
}

export function useCreatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createPersona,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}

export function useUpdatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<{ name: string; description: string; system_prompt: string; tone: string; rules: string; boundaries: string }> }) =>
      updatePersona(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}

export function useDeletePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deletePersona,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}
