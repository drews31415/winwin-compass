"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import type { AreaMapFeature } from "@/lib/hooks/useMapData";

// ── 공유 유틸리티 ─────────────────────────────────────────────────────────────

export function riskColor(score: number): string {
  if (score < 0.35) return "#52B788";
  if (score < 0.65) return "#F4A261";
  return "#E63946";
}

export function riskLabel(score: number): { text: string; cls: string } {
  if (score < 0.35) return { text: "낮음", cls: "risk-badge-low" };
  if (score < 0.65) return { text: "중간", cls: "risk-badge-mid" };
  return { text: "높음", cls: "risk-badge-high" };
}

export function formatSales(amount: number): string {
  if (amount >= 100_000_000) return `${(amount / 100_000_000).toFixed(1)}억원`;
  if (amount >= 10_000)      return `${Math.round(amount / 10_000)}만원`;
  return `${amount.toLocaleString("ko-KR")}원`;
}

function RiskDots({ score }: { score: number }) {
  const filled = Math.round(score * 5);
  return (
    <span className="flex items-center gap-0.5">
      {Array.from({ length: 5 }, (_, i) => (
        <span
          key={i}
          className="h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: i < filled ? riskColor(score) : "#E5E7EB" }}
        />
      ))}
    </span>
  );
}

// ── 팝업 컴포넌트 ─────────────────────────────────────────────────────────────

interface Props {
  area: AreaMapFeature;
  onClose?: () => void;
  compact?: boolean;
}

export function AreaPopup({ area, onClose, compact = false }: Props) {
  const risk = riskLabel(area.risk_score);

  return (
    <div
      className={cn(
        "flex flex-col rounded-2xl border border-gray-100 bg-white shadow-card-hover",
        compact ? "min-w-[220px] p-3" : "min-w-[260px] p-4",
      )}
    >
      {/* 헤더 */}
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-1.5 text-[11px] text-golmok-text-muted">
            <span>📍</span>
            <span>{area.gu_nm}</span>
            <span>·</span>
            <span>{area.area_type}</span>
          </div>
          <h3 className="mt-0.5 font-semibold text-golmok-text-main">{area.area_nm}</h3>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="shrink-0 rounded-md p-1 text-gray-400 hover:bg-gray-100"
            aria-label="닫기"
          >
            ✕
          </button>
        )}
      </div>

      {/* 데이터 테이블 */}
      <div className="mb-3 space-y-2 rounded-xl bg-gray-50 p-3">
        <Row label="월평균 매출" value={formatSales(area.monthly_sales_avg)} />
        <Row label="점포 수" value={`${area.store_count.toLocaleString("ko-KR")}개`} />
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">위험도</span>
          <div className="flex items-center gap-2">
            <RiskDots score={area.risk_score} />
            <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", risk.cls)}>
              {risk.text}
            </span>
          </div>
        </div>
      </div>

      {/* 액션 버튼 */}
      {!compact && (
        <div className="flex gap-2">
          <Link
            href={`/report?area=${area.area_cd}`}
            className={cn(
              "flex-1 rounded-xl bg-golmok-primary py-2 text-center text-xs font-medium text-white",
              "transition-colors hover:bg-golmok-primary-dark",
            )}
          >
            상세 리포트
          </Link>
          <Link
            href={`/chat?q=${encodeURIComponent(`${area.area_nm} 상권 분석해줘`)}`}
            className={cn(
              "flex-1 rounded-xl border border-golmok-primary py-2 text-center text-xs font-medium text-golmok-primary",
              "transition-colors hover:bg-golmok-primary/5",
            )}
          >
            AI에게 물어보기
          </Link>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-800">{value}</span>
    </div>
  );
}

// ── Mapbox 팝업용 HTML 생성 ──────────────────────────────────────────────────

export function createMapboxPopupHTML(area: AreaMapFeature): string {
  const risk = riskLabel(area.risk_score);
  const color = riskColor(area.risk_score);
  const dots = Array.from(
    { length: 5 },
    (_, i) =>
      `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${
        i < Math.round(area.risk_score * 5) ? color : "#E5E7EB"
      };margin-right:2px;"></span>`,
  ).join("");

  return `
<div style="font-family:Pretendard,sans-serif;min-width:220px;padding:12px;border-radius:14px;">
  <div style="font-size:10px;color:#6B7280;margin-bottom:2px;">
    📍 ${area.gu_nm} · ${area.area_type}
  </div>
  <div style="font-weight:600;font-size:14px;color:#1A1A1A;margin-bottom:10px;">${area.area_nm}</div>
  <div style="background:#F8F7F2;border-radius:10px;padding:10px;margin-bottom:10px;">
    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;">
      <span style="color:#6B7280;">월평균 매출</span>
      <span style="font-weight:500;">${formatSales(area.monthly_sales_avg)}</span>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;">
      <span style="color:#6B7280;">점포 수</span>
      <span style="font-weight:500;">${area.store_count.toLocaleString("ko-KR")}개</span>
    </div>
    <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;">
      <span style="color:#6B7280;">위험도</span>
      <div style="display:flex;align-items:center;gap:6px;">
        <div>${dots}</div>
        <span style="font-size:10px;background:${color}22;color:${color};border-radius:20px;padding:1px 8px;font-weight:500;">${risk.text}</span>
      </div>
    </div>
  </div>
  <div style="display:flex;gap:6px;">
    <a href="/report?area=${area.area_cd}" style="flex:1;background:#2D6A4F;color:#fff;border-radius:10px;padding:7px;text-align:center;font-size:11px;font-weight:500;text-decoration:none;">상세 리포트</a>
    <a href="/chat?q=${encodeURIComponent(area.area_nm + " 상권 분석해줘")}" style="flex:1;border:1px solid #2D6A4F;color:#2D6A4F;border-radius:10px;padding:7px;text-align:center;font-size:11px;font-weight:500;text-decoration:none;">AI 상담</a>
  </div>
</div>`;
}
