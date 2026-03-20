import { useParams, Link } from "react-router-dom";
import { FileText, ArrowLeft, Eye, EyeOff } from "lucide-react";
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
      <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center">
        <FileText className="w-12 h-12 text-gray-700 mb-4" />
        <p className="text-gray-500 text-sm">Document not found</p>
        <Link to="/dashboard" className="text-blue-400 hover:text-blue-300 text-sm mt-3 transition-colors">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-4 h-14 border-b border-gray-800 bg-gray-900/60 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to="/dashboard"
            className="flex items-center gap-1.5 text-gray-400 hover:text-white transition-all duration-200 rounded-md px-2 py-1.5 hover:bg-gray-800 -ml-2"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div className="w-px h-5 bg-gray-800" />
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-7 h-7 bg-blue-500/10 rounded-md flex items-center justify-center flex-shrink-0">
              <FileText className="w-3.5 h-3.5 text-blue-400" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm text-white font-semibold truncate max-w-[300px]">
                {doc?.filename ?? "Loading..."}
              </h1>
              {doc?.file_type && (
                <p className="text-xs text-gray-500">{doc.file_type.toUpperCase()}</p>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setOverlayMode(overlayMode === "none" ? "confidence" : "none")}
            className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-md transition-all duration-200 ${
              overlayMode !== "none"
                ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                : "text-gray-400 hover:text-white hover:bg-gray-800 border border-transparent"
            }`}
          >
            {overlayMode !== "none" ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
            Overlay
          </button>
          <div className="w-px h-5 bg-gray-800" />
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
        <div className="w-[420px] flex-shrink-0 border-l border-gray-800 flex flex-col bg-gray-950">
          {/* Tabs */}
          <div className="flex border-b border-gray-800 bg-gray-900/30">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`relative flex-1 text-sm py-3 font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-inset ${
                  activeTab === tab.id
                    ? "text-blue-400"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-blue-500 rounded-full" />
                )}
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
