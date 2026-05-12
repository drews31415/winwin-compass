"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getForecast, type ForecastResponse } from "@/lib/api";

type Props = {
  areaCd: string;
  history?: Array<{ quarter?: string; sales?: number; avg_sales?: number }>;
};

const SAMPLE_FORECAST: ForecastResponse = {
  area_cd: "3110016",
  area_nm: "종로3가",
  trend_summary: "최근 흐름은 보합권이며 향후 4분기 완만한 회복이 예상됩니다.",
  confidence: 0.72,
  forecast: [
    { quarter: "2025Q1", date: "2025-01-01", predicted_sales: 225000000, lower_bound: 188000000, upper_bound: 262000000, trend: "보합" },
    { quarter: "2025Q2", date: "2025-04-01", predicted_sales: 238000000, lower_bound: 198000000, upper_bound: 278000000, trend: "상승" },
    { quarter: "2025Q3", date: "2025-07-01", predicted_sales: 246000000, lower_bound: 205000000, upper_bound: 292000000, trend: "상승" },
    { quarter: "2025Q4", date: "2025-10-01", predicted_sales: 232000000, lower_bound: 190000000, upper_bound: 271000000, trend: "보합" },
  ],
  chart_data: { labels: [], predicted: [], lower: [], upper: [] },
};

function toEok(value?: number) {
  return Math.round(((value ?? 0) / 100000000) * 10) / 10;
}

export function ForecastChart({ areaCd, history = [] }: Props) {
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    getForecast(areaCd, 4)
      .then((result) => {
        if (alive) setData(result);
      })
      .catch((event: Error) => {
        if (!alive) return;
        setError(event.message);
        setData({ ...SAMPLE_FORECAST, area_cd: areaCd });
      });
    return () => {
      alive = false;
    };
  }, [areaCd]);

  const chartData = useMemo(() => {
    const actual = history.map((item) => ({
      quarter: item.quarter ?? "",
      actual: item.sales ?? toEok(item.avg_sales),
      predicted: null,
      lower: null,
      upper: null,
    }));
    const forecast = (data?.forecast ?? []).map((item) => ({
      quarter: item.quarter,
      actual: null,
      predicted: toEok(item.predicted_sales),
      lower: toEok(item.lower_bound),
      upper: toEok(item.upper_bound),
    }));
    return [...actual, ...forecast];
  }, [data, history]);

  const referenceQuarter = history.at(-1)?.quarter ?? chartData[Math.max(0, history.length - 1)]?.quarter;

  return (
    <section className="rounded-lg border border-golmok-primary/10 bg-white p-5 shadow-card">
      <div className="mb-4">
        <h2 className="text-xl font-black text-golmok-text-main">매출 예측</h2>
        <p className="text-sm text-golmok-text-muted">
          {data?.trend_summary ?? "향후 4분기 예측을 불러오는 중입니다."}
          {error ? " 샘플 예측 데이터를 표시합니다." : ""}
        </p>
      </div>
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="quarter" tickLine={false} axisLine={false} />
          <YAxis tickLine={false} axisLine={false} unit="억" />
          <Tooltip formatter={(value, name) => [`${value}억원`, name]} />
          <Legend />
          <Area name="신뢰구간" dataKey="upper" fill="#52B788" fillOpacity={0.12} stroke="none" />
          <Area dataKey="lower" fill="#FFFFFF" fillOpacity={1} stroke="none" legendType="none" />
          <Line name="실제 매출" type="monotone" dataKey="actual" stroke="#2D6A4F" strokeWidth={3} connectNulls={false} dot={{ r: 4 }} />
          <Line name="예측 매출" type="monotone" dataKey="predicted" stroke="#2D6A4F" strokeWidth={3} strokeDasharray="6 6" connectNulls={false} dot={{ r: 4 }} />
          {referenceQuarter && (
            <ReferenceLine x={referenceQuarter} stroke="#6B7280" strokeDasharray="4 4" label="현재" />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      <p className="mt-3 text-xs text-golmok-text-muted">
        모델 신뢰도: {Math.round((data?.confidence ?? 0) * 100)}%
      </p>
    </section>
  );
}
