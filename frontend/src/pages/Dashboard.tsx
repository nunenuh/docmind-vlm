import { useState } from "react";
import { FileText, LogOut, Loader2, FolderOpen, Upload, ChevronLeft, ChevronRight } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { signOut } from "@/lib/supabase";
import { useAuthStore } from "@/stores/auth-store";
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/hooks/useDocuments";
import { UploadArea } from "@/components/workspace/UploadArea";
import { DocumentCard } from "@/components/dashboard/DocumentCard";

type DashboardTab = "documents" | "projects";

export function Dashboard() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [page, setPage] = useState(1);
  const [activeTab, setActiveTab] = useState<DashboardTab>("documents");
  const limit = 20;

  const { data, isLoading } = useDocuments(page, limit);
  const uploadDoc = useUploadDocument();
  const deleteDoc = useDeleteDocument();

  const handleUpload = (file: File) => {
    uploadDoc.mutate(file);
  };

  const handleDelete = (id: string) => {
    deleteDoc.mutate(id);
  };

  const handleLogout = async () => {
    await signOut();
    navigate("/");
  };

  const documents = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="h-16 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2.5 text-white font-bold text-lg">
              <FileText className="w-5 h-5 text-blue-400" />
              DocMind-VLM
            </Link>
            <div className="flex items-center gap-4">
              {user && (
                <span className="text-sm text-gray-400 hidden sm:block truncate max-w-[200px]">
                  {user.email}
                </span>
              )}
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-all duration-200 rounded-md px-3 py-1.5 hover:bg-gray-800"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Page title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-gray-400">Manage your documents and projects in one place.</p>
        </div>

        {/* Tab navigation */}
        <div className="flex items-center gap-1 mb-8 border-b border-gray-800">
          <button
            onClick={() => setActiveTab("documents")}
            className={`relative px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
              activeTab === "documents"
                ? "text-blue-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Documents
            {activeTab === "documents" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-full" />
            )}
          </button>
          <button
            onClick={() => { setActiveTab("projects"); navigate("/projects"); }}
            className={`relative px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
              activeTab === "projects"
                ? "text-blue-400"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Projects
            {activeTab === "projects" && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500 rounded-full" />
            )}
          </button>
        </div>

        {/* Upload area */}
        <div className="mb-10">
          <UploadArea onUpload={handleUpload} isUploading={uploadDoc.isPending} />
        </div>

        {/* Document grid */}
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-24">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
            <p className="text-sm text-gray-500 mt-3">Loading documents...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24">
            <div className="w-20 h-20 rounded-2xl bg-gray-900 border border-gray-800 flex items-center justify-center mb-5">
              <FolderOpen className="w-10 h-10 text-gray-700" />
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">No documents yet</h3>
            <p className="text-gray-500 text-sm mb-6 max-w-sm text-center">
              Upload your first document to start extracting structured data with AI.
            </p>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Upload className="w-4 h-4" />
              <span>Drag and drop or click the upload area above</span>
            </div>
          </div>
        ) : (
          <>
            {/* Document count */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-400">
                {total} document{total !== 1 ? "s" : ""}
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {documents.map((doc) => (
                <DocumentCard key={doc.id} document={doc} onDelete={handleDelete} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-3 mt-10">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent rounded-md transition-all duration-200"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <span className="text-sm text-gray-500 px-2">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-gray-800 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent rounded-md transition-all duration-200"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
