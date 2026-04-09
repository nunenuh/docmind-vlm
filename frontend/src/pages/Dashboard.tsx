import { useState } from "react";
import { Loader2, Upload, ChevronLeft, ChevronRight, Plus, FileText, Image, Search, FolderOpen, Database, HardDrive } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/hooks/useDocuments";
import { fetchAnalytics } from "@/lib/api";
import { UploadArea } from "@/components/workspace/UploadArea";
import { DocumentCard } from "@/components/dashboard/DocumentCard";

export function Dashboard() {
  const [page, setPage] = useState(1);
  const [showUpload, setShowUpload] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const limit = 20;

  const { data, isLoading } = useDocuments(page, limit);
  const { data: analytics } = useQuery({ queryKey: ["analytics"], queryFn: fetchAnalytics, staleTime: 30_000 });
  const uploadDoc = useUploadDocument();
  const deleteDoc = useDeleteDocument();

  const handleUpload = (file: File) => {
    uploadDoc.mutate(file);
  };

  const handleDelete = (id: string) => {
    if (window.confirm("Are you sure you want to delete this document?")) {
      deleteDoc.mutate(id);
    }
  };

  const documents = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  // Filter by search query (client-side for now)
  const filtered = searchQuery
    ? documents.filter((d) => d.filename.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-white">Documents</h1>
          <p className="text-sm text-gray-400 mt-1">
            Upload documents for AI-powered extraction and analysis
          </p>
        </div>
        <button
          onClick={() => setShowUpload(!showUpload)}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/20"
        >
          <Plus className="w-4 h-4" />
          Upload Document
        </button>
      </div>

      {/* Stats row */}
      {(total > 0 || analytics) && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
          <StatCard
            label="Documents"
            value={(analytics?.documents as Record<string, unknown>)?.total as number ?? total}
            icon={<FileText className="w-4 h-4 text-indigo-400" />}
          />
          <StatCard
            label="Pages"
            value={analytics?.pages_processed as number ?? 0}
            icon={<FileText className="w-4 h-4 text-cyan-400" />}
          />
          <StatCard
            label="Projects"
            value={analytics?.projects as number ?? 0}
            icon={<FolderOpen className="w-4 h-4 text-violet-400" />}
          />
          <StatCard
            label="RAG Chunks"
            value={analytics?.rag_chunks as number ?? 0}
            icon={<Database className="w-4 h-4 text-amber-400" />}
          />
          <StatCard
            label="Ready"
            value={((analytics?.documents as Record<string, unknown>)?.by_status as Record<string, number>)?.ready ?? 0}
            icon={<Image className="w-4 h-4 text-emerald-400" />}
          />
          <StatCard
            label="Storage"
            value={`${analytics?.storage_mb ?? 0} MB`}
            icon={<HardDrive className="w-4 h-4 text-rose-400" />}
          />
        </div>
      )}

      {/* Upload area (collapsible) */}
      {showUpload && (
        <div className="mb-6 animate-in slide-in-from-top-2 duration-200">
          <UploadArea onUpload={handleUpload} isUploading={uploadDoc.isPending} />
        </div>
      )}

      {/* Search + filters */}
      {total > 0 && (
        <div className="flex items-center gap-3 mb-5">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#12121a] border border-[#1e1e2e] rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </div>
          <span className="text-xs text-gray-500 ml-auto">
            {filtered.length} of {total} document{total !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Document grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-24">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm text-gray-500 mt-3">Loading documents...</p>
        </div>
      ) : documents.length === 0 ? (
        <EmptyState onUpload={() => setShowUpload(true)} />
      ) : filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16">
          <Search className="w-8 h-8 text-gray-600 mb-3" />
          <p className="text-sm text-gray-400">No documents matching "{searchQuery}"</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {filtered.map((doc) => (
              <DocumentCard key={doc.id} document={doc} onDelete={handleDelete} />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 mt-8">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </button>
              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).slice(0, 5).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-8 h-8 text-sm rounded-lg transition-all ${
                      p === page
                        ? "bg-indigo-600 text-white"
                        : "text-gray-400 hover:text-white hover:bg-white/5"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed rounded-lg transition-all"
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

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: React.ReactNode }) {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl px-4 py-3">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-gray-500 font-medium">{label}</span>
      </div>
      <span className="text-xl font-semibold text-white">{value}</span>
    </div>
  );
}

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4">
      <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/10 to-violet-500/10 border border-indigo-500/20 flex items-center justify-center mb-6">
        <Upload className="w-10 h-10 text-indigo-400" />
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">No documents yet</h3>
      <p className="text-gray-500 text-sm mb-6 max-w-md text-center leading-relaxed">
        Upload PDFs or images to extract structured data using Vision Language Models.
        Each document can be processed, analyzed, and chatted with.
      </p>
      <button
        onClick={onUpload}
        className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-indigo-500/20"
      >
        <Plus className="w-4 h-4" />
        Upload Your First Document
      </button>
    </div>
  );
}
