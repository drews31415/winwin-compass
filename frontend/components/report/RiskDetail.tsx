"use client";

import { useEffect, useState } from "react";
import { getRisk, type RiskResponse } from "@/lib/api";

const SAMPLE_RISK: RiskResponse = {
  area_cd: "3110016",
  risk_score: 58,
  risk_level: "중간",
  risk_probability: 0.58,
  main_risk_factors: [
    { factor: "폐업률", value: "12.4%", contribution: 0.42, description: "최근 폐업률 수준이 평균보다 높습니다." },
    { factor: "매출 감소", value: "-7.8%", contribution: 0.31, description: "전년 동기 대비 매출 하락 압력이 있습니다." },
    { factor: "경쟁 심화", value: "점포 18.2% 증가", contribution: 0.18, description: "신규 점포 유입으로 경쟁 강도가 높아졌습니다." },
  ],
  score_breakdown: { sales_score: 45, store_score: 68, population_score: 52 },
  compared_to_avg: "+1점 (서울 평균 대비 유사)",
};

export function RiskDetail({ areaCd }: { areaCd: string }) {
  const [data, setData] = useState<RiskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getRisk(areaCd)
      .then((result) => {
        if (alive) setData(result);
      })
      .catch((event: Error) => {
        if (!alive) return;
        setError(event.message);
        setData({ ...SAMPLE_RISK, area_cd: areaCd });
      });
    return () => {
      alive = false;
    };
  }, [areaCd]);

  const risk = data ?? SAMPLE_RISK;

  return (
    <section className="rounded-lg border border-golmok-primary/10 bg-white p-5 shadow-card">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-black text-golmok-text-main">위험 요인 상세</h2>
          <p className="text-sm text-golmok-text-muted">
            {risk.compared_to_avg}
            {error ? " 샘플 위험도 데이터를 표시합니다." : ""}
          </p>
        </div>
        <span className="rounded-full bg-golmok-accent/15 px-3 py-1 text-sm font-bold text-golmok-accent">
          {risk.risk_score}점 · {risk.risk_level}
        </span>
      </div>

      <div className="space-y-4">
        {risk.main_risk_factors.slice(0, 3).map((factor) => (
          <div key={factor.factor}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-bold text-golmok-text-main">{factor.factor}</span>
              <span className="text-golmok-text-muted">{factor.value}</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-golmok-primary"
                style={{ width: `${Math.min(100, Math.round(factor.contribution * 100))}%` }}
              />
            </div>
            <p className="mt-1 text-sm leading-6 text-golmok-text-muted">{factor.description}</p>
          </div>
        ))}
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-xs font-semibold text-golmok-text-muted">
          <span>서울 평균</span>
          <span>현재 상권</span>
        </div>
        <div className="relative h-3 rounded-full bg-gradient-to-r from-golmok-risk-low via-golmok-accent to-golmok-risk-high">
          <span className="absolute top-1/2 h-5 w-0.5 -translate-y-1/2 bg-white shadow" style={{ left: "57%" }} />
          <span className="absolute top-1/2 h-6 w-2 -translate-y-1/2 rounded-full bg-golmok-text-main" style={{ left: `${risk.risk_score}%` }} />
        </div>
      </div>
    </section>
  );
}
