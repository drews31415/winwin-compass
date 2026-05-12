import { cn } from "@/lib/utils";

export function LoadingSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-lg bg-gradient-to-r from-gray-100 via-gray-200 to-gray-100",
        className,
      )}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-lg border border-gray-100 bg-white p-5 shadow-card">
      <LoadingSkeleton className="mb-4 h-5 w-2/3" />
      <LoadingSkeleton className="mb-2 h-4 w-full" />
      <LoadingSkeleton className="mb-5 h-4 w-4/5" />
      <LoadingSkeleton className="h-10 w-full" />
    </div>
  );
}
