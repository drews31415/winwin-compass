import type { LucideIcon } from "lucide-react";
import { SearchX } from "lucide-react";

type EmptyStateProps = {
  title?: string;
  description?: string;
  icon?: LucideIcon;
};

export function EmptyState({
  title = "데이터가 없습니다",
  description = "조건을 바꾸거나 다시 검색해 주세요.",
  icon: Icon = SearchX,
}: EmptyStateProps) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center rounded-lg border border-dashed border-gray-200 bg-white p-8 text-center">
      <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-md bg-golmok-primary/10 text-golmok-primary">
        <Icon className="h-6 w-6" />
      </span>
      <h3 className="text-base font-bold text-golmok-text-main">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-golmok-text-muted">{description}</p>
    </div>
  );
}
