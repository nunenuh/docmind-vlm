import { useState } from "react";
import { Loader2, FolderOpen, Upload, ChevronLeft, ChevronRight, Plus } from "lucide-react";
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/hooks/useDocuments";
import { UploadArea } from "@/components/workspace/UploadArea";
import { DocumentCard } from "@/components/dashboard/DocumentCard";

export function Dashboard() {
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
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

  const documents = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-white">Documents</h1>
          <p className="text-sm text-gray-400 mt-1">Upload and manage your documents</p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
        >
          <Plus className="w-4 h-4" />
          Upload Document
        </button>
      </div>

      {/* Collapsible upload area */}
      {showUpload && (
        <div className="mb-8">
          <UploadArea onUpload={handleUpload} isUploading={uploadDoc.isPending} />
        </div>
      )}

      {/* Document grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading documents...</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24">
          <div className="w-20 h-20 rounded-2xl bg-[#12121a] border border-[#1e1e2e] flex items-center justify-center mb-5">
            <FolderOpen className="w-10 h-10 text-gray-700" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">No documents yet</h3>
          <p className="text-gray-500 text-sm mb-6 max-w-sm text-center">
            Upload your first document to start extracting structured data with AI.
          </p>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <Upload className="w-4 h-4" />
            <span>Click "Upload Document" above to get started</span>
          </button>
        </div>
      ) : (
        <>
          {/* Document count */}
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-400">
              {total} document{total !== 1 ? "s" : ""}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
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
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent rounded-lg transition-all"
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
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-transparent rounded-lg transition-all"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
