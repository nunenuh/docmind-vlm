import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  fetchPersonas,
  createPersona,
  updatePersona,
  deletePersona,
  duplicatePersona,
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
      toast.success("Persona created");
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
    onError: (e: Error) => toast.error(`Failed: ${e.message}`),
  });
}

export function useUpdatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      updatePersona(id, data),
    onSuccess: () => {
      toast.success("Persona updated");
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
    onError: (e: Error) => toast.error(`Failed: ${e.message}`),
  });
}

export function useDeletePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deletePersona,
    onSuccess: () => {
      toast.success("Persona deleted");
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
    onError: (e: Error) => toast.error(`Failed: ${e.message}`),
  });
}

export function useDuplicatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: duplicatePersona,
    onSuccess: () => {
      toast.success("Persona duplicated");
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
    onError: (e: Error) => toast.error(`Failed: ${e.message}`),
  });
}
