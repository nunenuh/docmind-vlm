import { useQuery } from "@tanstack/react-query";
import { fetchTemplates, fetchTemplate } from "@/lib/api";

export function useTemplates() {
  return useQuery({ queryKey: ["templates"], queryFn: fetchTemplates, staleTime: 5 * 60_000 });
}

export function useTemplate(type: string) {
  return useQuery({ queryKey: ["template", type], queryFn: () => fetchTemplate(type), enabled: !!type, staleTime: 5 * 60_000 });
}
