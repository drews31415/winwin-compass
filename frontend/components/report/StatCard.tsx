import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { cn } from "@/lib/utils";

type StatCardProps = {
  icon: LucideIcon;
  label: string;
  value: string;
  delta?: number;
  tone?: "default" | "warning" | "danger";
};

export function StatCard({ icon: Icon, label, value, delta, tone = "default" }: StatCardProps) {
  const isPositive = (delta ?? 0) >= 0;

  return (
    <div className="rounded-lg border border-brand-primary/10 bg-white p-4 shadow-card">
      <div className="mb-4 flex items-center justify-between">
        <span
          className={cn(
            "flex h-10 w-10 items-center justify-center rounded-md",
            tone === "danger" && "bg-brand-risk-high/10 text-brand-risk-high",
            tone === "warning" && "bg-brand-accent/15 text-brand-accent",
            tone === "default" && "bg-brand-primary/10 text-brand-primary",
          )}
        >
          <Icon className="h-5 w-5" />
        </span>
        {typeof delta === "number" && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold",
              isPositive ? "bg-brand-risk-low/10 text-brand-risk-low" : "bg-brand-risk-high/10 text-brand-risk-high",
            )}
          >
            {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>
      <p className="text-sm text-brand-text-muted">{label}</p>
      <p className="mt-1 text-2xl font-black text-brand-text-main">{value}</p>
    </div>
  );
}
