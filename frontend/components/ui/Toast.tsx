"use client";

import { CheckCircle2, X, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastState = {
  message: string;
  type?: "success" | "error";
} | null;

type ToastProps = {
  toast: ToastState;
  onClose: () => void;
};

export function Toast({ toast, onClose }: ToastProps) {
  if (!toast) return null;

  const isError = toast.type === "error";
  const Icon = isError ? XCircle : CheckCircle2;

  return (
    <div
      className={cn(
        "fixed right-4 top-4 z-50 flex max-w-sm items-center gap-3 rounded-lg border bg-white px-4 py-3 shadow-card-hover",
        isError ? "border-golmok-risk-high/30" : "border-golmok-risk-low/30",
      )}
      role="status"
    >
      <Icon className={cn("h-5 w-5 shrink-0", isError ? "text-golmok-risk-high" : "text-golmok-risk-low")} />
      <p className="text-sm font-medium text-golmok-text-main">{toast.message}</p>
      <button type="button" onClick={onClose} className="ml-2 rounded-md p-1 text-gray-400 hover:bg-gray-100">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
