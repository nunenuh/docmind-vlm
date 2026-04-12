interface EmbeddingBadgeProps {
  status: string;
  indexedChunks?: number;
  totalChunks?: number;
}

const badgeConfig: Record<string, { label: string; className: string }> = {
  indexed: {
    label: "Indexed",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  partial: {
    label: "Partial",
    className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  not_indexed: {
    label: "Not indexed",
    className: "bg-gray-500/10 text-gray-400 border-gray-500/20",
  },
  no_chunks: {
    label: "No chunks",
    className: "bg-gray-500/10 text-gray-500 border-gray-500/20",
  },
};

export function EmbeddingBadge({ status, indexedChunks, totalChunks }: EmbeddingBadgeProps) {
  const config = badgeConfig[status] ?? badgeConfig.not_indexed;

  const label =
    status === "partial" && indexedChunks != null && totalChunks != null
      ? `${indexedChunks}/${totalChunks} chunks`
      : config.label;

  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${config.className}`}
    >
      {label}
    </span>
  );
}
