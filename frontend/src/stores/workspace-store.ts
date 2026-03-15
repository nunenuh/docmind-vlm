import { create } from "zustand";

interface WorkspaceState {
  activeTab: "extraction" | "chat" | "audit" | "compare";
  overlayMode: "none" | "confidence" | "bounding_box";
  selectedFieldId: string | null;
  zoomLevel: number;
  isProcessing: boolean;
  setActiveTab: (tab: WorkspaceState["activeTab"]) => void;
  setOverlayMode: (mode: WorkspaceState["overlayMode"]) => void;
  selectField: (fieldId: string | null) => void;
  setZoomLevel: (level: number) => void;
  setIsProcessing: (processing: boolean) => void;
  resetWorkspace: () => void;
}

const INITIAL_STATE = {
  activeTab: "extraction" as const,
  overlayMode: "none" as const,
  selectedFieldId: null,
  zoomLevel: 1.0,
  isProcessing: false,
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  ...INITIAL_STATE,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setOverlayMode: (mode) => set({ overlayMode: mode }),
  selectField: (fieldId) => set({ selectedFieldId: fieldId }),
  setZoomLevel: (level) => set({ zoomLevel: Math.max(0.25, Math.min(5.0, level)) }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  resetWorkspace: () => set(INITIAL_STATE),
}));
