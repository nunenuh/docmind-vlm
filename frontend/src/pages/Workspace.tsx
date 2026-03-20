import { useParams, Link } from "react-router-dom";
import { FileText, ChevronRight, Eye, EyeOff } from "lucide-react";
import { useWorkspaceStore } from "@/stores/workspace-store";
import { useDocument, useDocumentUrl } from "@/hooks/useDocuments";
import { DocumentViewer } from "@/components/workspace/DocumentViewer";
import { ExtractionPanel } from "@/components/workspace/ExtractionPanel";
import { AuditPanel } from "@/components/workspace/AuditPanel";
import { ChatPanel } from "@/components/workspace/ChatPanel";
import { ComparePanel } from "@/components/workspace/ComparePanel";
import { ProcessingProgress } from "@/components/workspace/ProcessingProgress";

type TabId = "extraction" | "chat" | "audit" | "compare";

const tabs: { id: TabId; label: string }[] = [
  { id: "extraction", label: "Extraction" },
  { id: "chat", label: "Chat" },
  { id: "audit", label: "Audit" },
  { id: "compare", label: "Compare" },
];

export function Workspace() {
  const { documentId } = useParams<{ documentId: string }>();
  const { activeTab, setActiveTab, overlayMode, setOverlayMode } = useWorkspaceStore();
  const { data: doc } = useDocument(documentId ?? "");
  const { data: urlData } = useDocumentUrl(documentId ?? "");

  if (!documentId) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <FileText className="w-12 h-12 text-gray-700 mb-4" />
        <p className="text-gray-500 text-sm">Document not found</p>
        <Link to="/dashboard" className="text-indigo-400 hover:text-indigo-300 text-sm mt-3 transition-colors">
          Back to Documents
        </Link>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#0a0a0f]">
      {/* Breadcrumb header */}
      <header className="flex items-center justify-between px-4 h-12 border-b border-[#1e1e2e] bg-[#12121a] flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0 text-sm">
          <Link to="/dashboard" className="text-gray-500 hover:text-gray-300 transition-colors">
            Documents
          </Link>
          <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
          <span className="text-white font-medium truncate max-w-[300px]">
            {doc?.filename ?? "Loading..."}
          </span>
          {doc?.file_type && (
            <span className="text-xs text-gray-500 bg-white/5 px-1.5 py-0.5 rounded ml-1">
              {doc.file_type.toUpperCase()}
            </span>
          )}
        </div>
        <button
          onClick={() => setOverlayMode(overlayMode === "none" ? "confidence" : "none")}
          className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-all border ${
            overlayMode !== "none"
              ? "bg-indigo-500/10 text-indigo-300 border-indigo-500/20"
              : "text-gray-400 hover:text-white hover:bg-white/5 border-transparent"
          }`}
        >
          {overlayMode !== "none" ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
          Overlay
        </button>
      </header>

      {/* Split layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Document viewer */}
        <div className="flex-1 min-w-0">
          <DocumentViewer imageUrl={urlData?.url} />
        </div>

        {/* Right: Panel */}
        <div className="w-[420px] flex-shrink-0 border-l border-[#1e1e2e] flex flex-col bg-[#0a0a0f]">
          {/* Tabs */}
          <div className="flex border-b border-[#1e1e2e] bg-[#12121a]">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex-1 text-sm py-3 font-medium transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-inset ${
                  activeTab === tab.id
                    ? "text-indigo-400"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-500 rounded-full" />
                )}
              </button>
            ))}
          </div>

          {/* Processing progress inline (inside extraction panel area) */}
          {activeTab === "extraction" && (
            <div className="px-4 py-3 border-b border-[#1e1e2e]">
              <ProcessingProgress documentId={documentId} />
            </div>
          )}

          {/* Tab content */}
          <div className="flex-1 overflow-hidden">
            {activeTab === "extraction" && <ExtractionPanel documentId={documentId} />}
            {activeTab === "chat" && <ChatPanel documentId={documentId} />}
            {activeTab === "audit" && <AuditPanel documentId={documentId} />}
            {activeTab === "compare" && <ComparePanel documentId={documentId} />}
          </div>
        </div>
      </div>
    </div>
  );
}
