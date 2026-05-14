"use client";

import { useEffect, useMemo, useState } from "react";
import { getRisk, type RiskFactor, type RiskResponse } from "@/lib/api";

const FALLBACK_RISK: RiskResponse = {
  area_cd: "",
  risk_score: 0,
  risk_level: "낮음",
  risk_probability: 0,
  main_risk_factors: [],
  score_breakdown: { sales_score: 0, store_score: 0, population_score: 0 },
  compared_to_avg: "서울 평균과 비교할 데이터가 부족합니다.",
};

const FACTOR_LABELS: Record<string, string> = {
  close_rate: "폐업률",
  store_count: "점포 수",
  store_growth_qoq: "점포 증감",
  competition_index: "경쟁 강도",
  monthly_sales_avg: "매출 규모",
  sales_growth_qoq: "전분기 매출 변화",
  sales_growth_yoy: "전년 매출 변화",
  sales_volatility: "매출 변동성",
  sales_per_store: "점포당 매출",
  sales_per_population: "유동인구당 매출",
  population_growth_qoq: "유동인구 변화",
  worker_ratio: "직장인구 비중",
  young_ratio: "20-30대 비중",
  risk_trend_3q: "최근 폐업률 변화",
  quarters_since_peak: "매출 정점 이후 기간",
};

function normalizeFactor(factor: RiskFactor): RiskFactor {
  const key = factor.factor;
  const label = FACTOR_LABELS[key] ?? key;
  const isInternalKey = key === label && /^[a-z0-9_]+$/.test(key);

  return {
    ...factor,
    factor: isInternalKey ? "위험 변수" : label,
    description:
      factor.description && !factor.description.includes("모델이 주요 위험 변수")
        ? factor.description
        : `${label} 지표가 현재 위험 점수에 반영되었습니다.`,
  };
}

function levelLabel(score: number) {
  if (score >= 70) return "높음";
  if (score >= 40) return "중간";
  return "낮음";
}

export function RiskDetail({ areaCd }: { areaCd: string }) {
  const [data, setData] = useState<RiskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    getRisk(areaCd)
      .then((result) => {
        if (alive) setData(result);
      })
      .catch((event: Error) => {
        if (!alive) return;
        setError(event.message);
        setData({ ...FALLBACK_RISK, area_cd: areaCd });
      });
    return () => {
      alive = false;
    };
  }, [areaCd]);

  const risk = data ?? FALLBACK_RISK;
  const factors = useMemo(
    () => risk.main_risk_factors.slice(0, 3).map(normalizeFactor),
    [risk.main_risk_factors],
  );
  const markerPosition = Math.min(98, Math.max(0, risk.risk_score));
  const displayLevel = risk.risk_level && !risk.risk_level.includes("?") ? risk.risk_level : levelLabel(risk.risk_score);

  return (
    <section className="rounded-lg border border-brand-primary/10 bg-white p-5 shadow-card">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-brand-text-main">위험 요인 상세</h2>
          <p className="text-sm text-brand-text-muted">
            {error ? "위험 상세 데이터를 불러오지 못했습니다." : risk.compared_to_avg}
          </p>
        </div>
        <span className="rounded-full bg-brand-accent/15 px-3 py-1 text-sm font-bold text-brand-accent">
          {Math.round(risk.risk_score)}점 · {displayLevel}
        </span>
      </div>

      {factors.length > 0 ? (
        <div className="space-y-4">
          {factors.map((factor) => (
            <div key={factor.factor}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-bold text-brand-text-main">{factor.factor}</span>
                <span className="text-brand-text-muted">{factor.value}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-gray-100">
                <div
                  className="h-full rounded-full bg-brand-primary"
                  style={{ width: `${Math.min(100, Math.max(6, Math.round(factor.contribution * 100)))}%` }}
                />
              </div>
              <p className="mt-1 text-sm leading-6 text-brand-text-muted">{factor.description}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-brand-text-muted">
          이 상권은 위험 요인을 산출할 만큼의 비교 데이터가 아직 부족합니다.
        </p>
      )}

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-xs font-semibold text-brand-text-muted">
          <span>서울 평균</span>
          <span>현재 상권</span>
        </div>
        <div className="relative h-3 rounded-full bg-gradient-to-r from-brand-risk-low via-brand-accent to-brand-risk-high">
          <span className="absolute top-1/2 h-5 w-0.5 -translate-y-1/2 bg-white shadow" style={{ left: "57%" }} />
          <span className="absolute top-1/2 h-6 w-2 -translate-y-1/2 rounded-full bg-brand-text-main" style={{ left: `${markerPosition}%` }} />
        </div>
      </div>
    </section>
  );
}
