import Link from "next/link";
import { Building2, CalendarDays, ExternalLink, FileText, WalletCards } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Policy } from "@/lib/api";

function policyTitle(policy: Policy) {
  return policy.program_nm ?? policy.title ?? "지원 정책";
}

function agency(policy: Policy) {
  return policy.agency ?? policy.target ?? "공공 지원기관";
}

function amount(policy: Policy) {
  if (policy.budget_max) return `최대 ${policy.budget_max.toLocaleString()}만원`;
  if (policy.budget_min) return `${policy.budget_min.toLocaleString()}만원 이상`;
  return "지원금액 확인 필요";
}

function fitScore(policy: Policy) {
  const raw = policy.match_score ?? policy.score ?? 0.86;
  const normalized = raw <= 1 ? raw * 100 : raw;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

function fitLabel(score: number) {
  if (score >= 85) return "매우 적합";
  if (score >= 70) return "적합";
  if (score >= 50) return "검토 가능";
  return "조건 확인";
}

export function PolicyCard({ policy }: { policy: Policy }) {
  const score = fitScore(policy);
  const title = policyTitle(policy);
  const href = policy.source_url || "#";
  const reason = policy.match_reason ?? policy.reason ?? policy.description;

  return (
    <article className="rounded-lg border border-brand-primary/10 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:border-brand-primary/40 hover:shadow-card-hover">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <span className="rounded-full bg-brand-primary/10 px-2.5 py-1 text-xs font-bold text-brand-primary">
            {policy.category ?? "지원사업"}
          </span>
          <h3 className="mt-3 text-lg font-black leading-snug text-brand-text-main">{title}</h3>
          {policy.badges?.length ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {policy.badges.slice(0, 4).map((badge) => (
                <span key={badge} className="rounded-full bg-brand-accent/15 px-2 py-0.5 text-[11px] font-bold text-brand-accent">
                  {badge}
                </span>
              ))}
            </div>
          ) : null}
        </div>
        <FileText className="h-5 w-5 shrink-0 text-brand-primary" />
      </div>

      <div className="space-y-2 text-sm text-brand-text-muted">
        <p className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-brand-primary" />
          {agency(policy)}
        </p>
        <p className="flex items-center gap-2 font-semibold text-brand-text-main">
          <WalletCards className="h-4 w-4 text-brand-primary" />
          {amount(policy)}
        </p>
        <p className="flex items-center gap-2">
          <CalendarDays className="h-4 w-4 text-brand-primary" />
          신청기간: {policy.apply_end ? `~${policy.apply_end}` : "공고 확인"}
        </p>
      </div>

      {reason && (
        <p className="mt-4 line-clamp-2 text-sm leading-6 text-brand-text-muted">
          {reason}
        </p>
      )}

      <div className="mt-5">
        <div className="mb-2 flex items-center justify-between text-xs font-semibold">
          <span className="text-brand-text-muted">적합도</span>
          <span className="text-brand-primary">{fitLabel(score)}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-gray-100">
          <div className="h-full rounded-full bg-brand-primary" style={{ width: `${score}%` }} />
        </div>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-2">
        <Button variant="outline" className="border-brand-primary/30 text-brand-primary hover:bg-brand-primary/10">
          자세히 보기
        </Button>
        <Button asChild className="bg-brand-primary hover:bg-brand-primary-dark">
          <Link href={href} target={href === "#" ? undefined : "_blank"} rel="noreferrer">
            신청하기
            <ExternalLink className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>
    </article>
  );
}
