import {
  FileText, FolderOpen, Database, HardDrive, Users, Layers,
  Loader2, TrendingUp,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchAnalytics } from "@/lib/api";

export function AnalyticsPage() {
  const { data: analytics, isLoading } = useQuery({
    queryKey: ["analytics"],
    queryFn: fetchAnalytics,
    staleTime: 30_000,
  });

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#0B0D11]">
        <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" />
      </div>
    );
  }

  const stats = analytics ?? {};
  const docCount = (stats.document_count as number) ?? 0;
  const pageCount = (stats.total_pages as number) ?? 0;
  const chunkCount = (stats.chunk_count as number) ?? 0;
  const projectCount = (stats.project_count as number) ?? 0;
  const personaCount = (stats.persona_count as number) ?? 0;
  const storageBytes = (stats.total_storage as number) ?? 0;
  const statusCounts = (stats.status_counts as Record<string, number>) ?? {};
  const typeCounts = (stats.type_counts as Record<string, number>) ?? {};

  const formatStorage = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  return (
    <div className="h-full bg-[#0B0D11] overflow-y-auto">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-xl font-bold text-gray-100">Analytics</h1>
          <p className="text-[13px] text-gray-500 mt-1">
            Overview of your documents, projects, and RAG pipeline.
          </p>
        </div>

        {/* Primary stats */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
          <MetricCard icon={FileText} label="Documents" value={docCount} color="indigo" />
          <MetricCard icon={Layers} label="Pages" value={pageCount} color="violet" />
          <MetricCard icon={FolderOpen} label="Projects" value={projectCount} color="emerald" />
          <MetricCard icon={Database} label="RAG Chunks" value={chunkCount} color="amber" />
          <MetricCard icon={Users} label="Personas" value={personaCount} color="rose" />
          <MetricCard icon={HardDrive} label="Storage" value={formatStorage(storageBytes)} color="cyan" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Document status breakdown */}
          <div className="p-5 bg-[#111318] border border-white/[0.05] rounded-xl">
            <h3 className="text-[13px] font-semibold text-gray-200 mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-indigo-400" />
              Document Status
            </h3>
            {Object.keys(statusCounts).length === 0 ? (
              <p className="text-[12px] text-gray-600">No data yet</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(statusCounts).map(([status, count]) => (
                  <BarRow
                    key={status}
                    label={status}
                    value={count}
                    max={docCount}
                    color={status === "ready" ? "emerald" : status === "error" ? "rose" : "indigo"}
                  />
                ))}
              </div>
            )}
          </div>

          {/* File type breakdown */}
          <div className="p-5 bg-[#111318] border border-white/[0.05] rounded-xl">
            <h3 className="text-[13px] font-semibold text-gray-200 mb-4 flex items-center gap-2">
              <FileText className="w-4 h-4 text-violet-400" />
              File Types
            </h3>
            {Object.keys(typeCounts).length === 0 ? (
              <p className="text-[12px] text-gray-600">No data yet</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(typeCounts).map(([type, count]) => (
                  <BarRow
                    key={type}
                    label={type.toUpperCase()}
                    value={count}
                    max={docCount}
                    color="violet"
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ──────────────────────── */

const COLOR_MAP: Record<string, string> = {
  indigo: "bg-indigo-500/10 text-indigo-400 border-indigo-500/10",
  violet: "bg-violet-500/10 text-violet-400 border-violet-500/10",
  emerald: "bg-emerald-500/10 text-emerald-400 border-emerald-500/10",
  amber: "bg-amber-500/10 text-amber-400 border-amber-500/10",
  rose: "bg-rose-500/10 text-rose-400 border-rose-500/10",
  cyan: "bg-cyan-500/10 text-cyan-400 border-cyan-500/10",
};

const ICON_COLOR_MAP: Record<string, string> = {
  indigo: "text-indigo-400",
  violet: "text-violet-400",
  emerald: "text-emerald-400",
  amber: "text-amber-400",
  rose: "text-rose-400",
  cyan: "text-cyan-400",
};

function MetricCard({
  icon: Icon, label, value, color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number | string;
  color: string;
}) {
  return (
    <div className={`px-4 py-3 rounded-xl border ${COLOR_MAP[color] || COLOR_MAP.indigo}`}>
      <div className="flex items-center gap-2 mb-1.5">
        <Icon className={`w-3.5 h-3.5 ${ICON_COLOR_MAP[color]}`} />
        <span className="text-[10px] uppercase tracking-wider text-gray-500">{label}</span>
      </div>
      <p className="text-lg font-bold text-gray-100">{value}</p>
    </div>
  );
}

const BAR_COLORS: Record<string, string> = {
  indigo: "bg-indigo-500",
  violet: "bg-violet-500",
  emerald: "bg-emerald-500",
  rose: "bg-rose-500",
  amber: "bg-amber-500",
};

function BarRow({
  label, value, max, color,
}: {
  label: string;
  value: number;
  max: number;
  color: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] text-gray-400 capitalize">{label}</span>
        <span className="text-[11px] font-medium text-gray-300">{value}</span>
      </div>
      <div className="h-1.5 bg-white/[0.04] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${BAR_COLORS[color] || BAR_COLORS.indigo}`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
    </div>
  );
}
