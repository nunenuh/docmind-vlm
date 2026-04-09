interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse bg-[#1a1a25] rounded-lg ${className}`}
    />
  );
}

export function DocumentCardSkeleton() {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4">
      <div className="flex items-start gap-3 mb-3">
        <Skeleton className="w-10 h-10 rounded-lg" />
        <div className="flex-1">
          <Skeleton className="h-4 w-3/4 mb-2" />
          <Skeleton className="h-3 w-1/3" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Skeleton className="h-3 w-16" />
        <Skeleton className="h-4 w-10 rounded" />
        <Skeleton className="h-3 w-12 ml-auto" />
      </div>
    </div>
  );
}

export function ProjectCardSkeleton() {
  return (
    <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-4">
      <div className="flex items-start gap-3 mb-3">
        <Skeleton className="w-10 h-10 rounded-lg" />
        <div className="flex-1">
          <Skeleton className="h-4 w-2/3 mb-2" />
          <Skeleton className="h-3 w-full" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-16 rounded-full" />
        <Skeleton className="h-3 w-24 ml-auto" />
      </div>
    </div>
  );
}

export function ChatMessageSkeleton() {
  return (
    <div className="flex gap-3">
      <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
      <div className="flex-1 max-w-[80%]">
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-5/6 mb-2" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  );
}

export function ExtractionFieldSkeleton() {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 border-b border-[#1e1e2e]">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-3 w-32 ml-auto" />
      <Skeleton className="h-4 w-8 rounded" />
    </div>
  );
}
