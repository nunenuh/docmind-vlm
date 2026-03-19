import { useParams, Link } from "react-router-dom";
import { FileText, ArrowLeft, Eye, EyeOff, Loader2 } from "lucide-react";
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
  const { data: doc, isLoading: docLoading } = useDocument(documentId ?? "");
  const { data: urlData } = useDocumentUrl(documentId ?? "");

  if (!documentId) {
    return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-gray-500">Document not found</div>;
  }

  return (
    <div className="h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-4 h-12 border-b border-gray-800 bg-gray-900/50 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link to="/dashboard" className="text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <FileText className="w-4 h-4 text-blue-400" />
          <span className="text-sm text-white font-medium truncate max-w-[200px]">
            {doc?.filename ?? documentId}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setOverlayMode(overlayMode === "none" ? "confidence" : "none")}
            className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-colors ${
              overlayMode !== "none"
                ? "bg-blue-500/20 text-blue-300"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {overlayMode !== "none" ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Overlay
          </button>
          <ProcessingProgress documentId={documentId} />
        </div>
      </header>

      {/* Split layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Document viewer */}
        <div className="flex-1 min-w-0">
          <DocumentViewer imageUrl={urlData?.url} />
        </div>

        {/* Right: Sidebar */}
        <div className="w-[400px] flex-shrink-0 border-l border-gray-800 flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-gray-800">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 text-sm py-2.5 font-medium transition-colors ${
                  activeTab === tab.id
                    ? "text-blue-400 border-b-2 border-blue-400"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

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
