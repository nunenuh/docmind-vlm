interface ConfidenceBadgeProps {
  confidence: number;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const pct = Math.round(confidence * 100);

  let className: string;
  if (confidence >= 0.8) {
    className = "bg-green-900/50 text-green-300";
  } else if (confidence >= 0.5) {
    className = "bg-yellow-900/50 text-yellow-300";
  } else {
    className = "bg-red-900/50 text-red-300";
  }

  return (
    <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full ${className}`}>
      {pct}%
    </span>
  );
}
