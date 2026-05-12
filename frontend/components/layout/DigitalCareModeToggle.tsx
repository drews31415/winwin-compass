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
    <button
      type="button"
      onClick={() => setEnabled(!enabled)}
      aria-pressed={enabled}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border bg-white font-semibold shadow-card transition",
        enabled
          ? "border-brand-primary text-brand-primary"
          : "border-gray-200 text-gray-600 hover:border-brand-primary/40 hover:text-brand-primary",
        compact ? "px-3 py-2 text-xs" : "px-4 py-2.5 text-sm",
      )}
    >
      <Accessibility className={compact ? "h-4 w-4" : "h-5 w-5"} />
      <span>{enabled ? "큰 글씨 모드 ON" : "디지털 약자 모드"}</span>
    </button>
  );
}
