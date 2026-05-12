"use client";

import { Accessibility } from "lucide-react";
import { useDigitalCareMode } from "@/lib/hooks/useDigitalCareMode";
import { cn } from "@/lib/utils";

type Props = {
  compact?: boolean;
};

export function DigitalCareModeToggle({ compact = false }: Props) {
  const { enabled, setEnabled } = useDigitalCareMode();

  return (
    <div className={cn("flex flex-col items-end gap-2", !compact && "items-center")}>
      <button
        type="button"
        onClick={() => setEnabled(!enabled)}
        aria-pressed={enabled}
        className={cn(
          "inline-flex items-center gap-2 rounded-full border bg-white font-semibold shadow-card transition",
          enabled
            ? "border-brand-primary bg-brand-primary text-white"
            : "border-gray-200 text-gray-600 hover:border-brand-primary/40 hover:text-brand-primary",
          compact ? "px-3 py-2 text-xs" : "px-5 py-3 text-base",
        )}
      >
        <Accessibility className={compact ? "h-4 w-4" : "h-5 w-5"} />
        <span>{enabled ? "큰 글씨 모드 ON" : "디지털 약자 모드"}</span>
      </button>
      {enabled && (
        <div
          className={cn(
            "rounded-lg border border-brand-primary/20 bg-white px-3 py-2 text-brand-primary shadow-card",
            compact ? "max-w-56 text-xs" : "max-w-sm text-sm",
          )}
        >
          글씨와 버튼이 크게 표시됩니다. 채팅에서는 마이크 음성 입력도 함께 사용할 수 있습니다.
        </div>
      )}
    </div>
  );
}
