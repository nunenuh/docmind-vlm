import { useQuery } from "@tanstack/react-query";
import { fetchExtraction, fetchAuditTrail, fetchOverlay, fetchComparison } from "@/lib/api";

export function useExtraction(documentId: string) {
  return useQuery({ queryKey: ["extraction", documentId], queryFn: () => fetchExtraction(documentId), enabled: !!documentId });
}

export function useAuditTrail(documentId: string) {
  return useQuery({ queryKey: ["audit-trail", documentId], queryFn: () => fetchAuditTrail(documentId), enabled: !!documentId });
}

export function useOverlay(documentId: string) {
  return useQuery({ queryKey: ["overlay", documentId], queryFn: () => fetchOverlay(documentId), enabled: !!documentId });
}

export function useComparison(documentId: string) {
  return useQuery({ queryKey: ["comparison", documentId], queryFn: () => fetchComparison(documentId), enabled: !!documentId });
}
