"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  Radar,
  RadarChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Bot, Building2, ExternalLink, Percent, ReceiptText, Store, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RiskGauge } from "@/components/report/RiskGauge";
import { StatCard } from "@/components/report/StatCard";
import { ForecastChart } from "@/components/report/ForecastChart";
import { RiskDetail } from "@/components/report/RiskDetail";

type ReportPolicy = {
  id?: string;
  program_nm?: string;
  title?: string;
  category?: string;
  source_url?: string;
  apply_end?: string;
  budget_min?: number;
  budget_max?: number;
  content?: string;
  reason?: string;
};

type ReportResponse = {
  area_nm: string;
  gu_nm?: string;
  area_type?: string;
  risk_score: number;
  report_md: string;
  charts: {
    sales_trend: Array<{ quarter?: string; year_quarter?: string; avg_sales?: number; sales?: number }>;
    time_slots: Array<{ slot?: string; time?: string; amount?: number; ratio?: number }>;
    age_distribution: Array<{ age_group?: string; age?: string; count?: number; resident?: number; worker?: number }>;
  };
  matched_policies: ReportPolicy[];
  summary?: {
    monthly_sales_avg?: number;
    store_count?: number;
    open_rate?: number;
    close_rate?: number;
  };
};

const AREA_META: Record<string, { area_nm: string; gu_nm: string; area_type: string }> = {
  "3110016": { area_nm: "종로3가", gu_nm: "종로구", area_type: "골목상권" },
  "3130210": { area_nm: "홍대입구", gu_nm: "마포구", area_type: "발달상권" },
  "3120190": { area_nm: "연남동", gu_nm: "마포구", area_type: "골목상권" },
  "3111042": { area_nm: "성수역", gu_nm: "성동구", area_type: "발달상권" },
  "3130154": { area_nm: "신촌역", gu_nm: "서대문구", area_type: "발달상권" },
};

const RECENT_KEY = "golmok-recent-reports";
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function sampleReport(areaCd: string): ReportResponse {
  const meta = AREA_META[areaCd] ?? { area_nm: "종로3가", gu_nm: "종로구", area_type: "골목상권" };

  return {
    ...meta,
    risk_score: 58,
    summary: {
      monthly_sales_avg: 230000000,
      store_count: 147,
      open_rate: 12.3,
      close_rate: 8.1,
    },
    charts: {
      sales_trend: [
        { quarter: "2022Q1", avg_sales: 185000000 },
        { quarter: "2022Q2", avg_sales: 194000000 },
        { quarter: "2022Q3", avg_sales: 202000000 },
        { quarter: "2022Q4", avg_sales: 213000000 },
        { quarter: "2023Q1", avg_sales: 218000000 },
        { quarter: "2023Q2", avg_sales: 225000000 },
        { quarter: "2023Q3", avg_sales: 231000000 },
        { quarter: "2024Q3", avg_sales: 230000000 },
      ],
      time_slots: [
        { slot: "06시", ratio: 6 },
        { slot: "09시", ratio: 10 },
        { slot: "12시", ratio: 23 },
        { slot: "15시", ratio: 18 },
        { slot: "18시", ratio: 29 },
        { slot: "21시", ratio: 14 },
      ],
      age_distribution: [
        { age_group: "10대", resident: 8, worker: 3 },
        { age_group: "20대", resident: 31, worker: 24 },
        { age_group: "30대", resident: 27, worker: 36 },
        { age_group: "40대", resident: 16, worker: 22 },
        { age_group: "50대", resident: 11, worker: 11 },
        { age_group: "60대", resident: 7, worker: 4 },
      ],
    },
    report_md: `## 상권 종합 평가
${meta.area_nm} 상권은 점심과 저녁 매출 비중이 높고 20~30대 방문 수요가 안정적인 편입니다.

## 매출 현황
월평균 매출은 약 2.3억원 수준이며 최근 3년간 완만한 상승 흐름을 보입니다.

## 유동인구 분석
20~30대 생활인구와 30~40대 직장인구가 함께 관찰되어 평일 점심, 퇴근 시간대 운영 전략이 중요합니다.

## 위험 신호
폐업률은 8%대로 낮지는 않습니다. 유사 업종 밀집도가 높아 임대료와 차별화 전략을 함께 검토해야 합니다.

## 기회 요인
저녁 시간대 매출 비중이 높아 예약, 포장, 세트 메뉴 중심의 객단가 개선 여지가 있습니다.

## 추천 업종
- 소형 카페: 회전율과 테이크아웃 수요를 활용할 수 있습니다.
- 캐주얼 다이닝: 점심과 저녁 피크를 모두 노릴 수 있습니다.
- 생활서비스: 상주 인구와 직장인 반복 수요에 적합합니다.`,
    matched_policies: [
      {
        program_nm: "소상공인 정책자금",
        category: "융자",
        budget_max: 7000,
        apply_end: "2026-06-30",
        source_url: "https://www.semas.or.kr",
      },
      {
        program_nm: "서울시 골목상권 활성화 지원",
        category: "보조금",
        budget_max: 3000,
        apply_end: "2026-07-31",
        source_url: "https://www.seoul.go.kr",
      },
      {
        program_nm: "서울신용보증재단 창업보증",
        category: "보증",
        budget_max: 10000,
        apply_end: "상시",
        source_url: "https://www.seoulshinbo.co.kr",
      },
    ],
  };
}

function formatMoney(value?: number) {
  if (!value) return "2.3억";
  if (value >= 100000000) return `${(value / 100000000).toFixed(1)}억`;
  if (value >= 10000) return `${Math.round(value / 10000).toLocaleString()}만`;
  return value.toLocaleString();
}

function normalizeReport(data: ReportResponse, areaCd: string): ReportResponse {
  const meta = AREA_META[areaCd] ?? {};
  const salesTrend = data.charts.sales_trend.map((item) => ({
    quarter: item.quarter ?? item.year_quarter ?? "",
    sales: Math.round(((item.avg_sales ?? item.sales ?? 0) / 100000000) * 10) / 10,
  }));

  const rawTimeSlots = data.charts.time_slots.map((item) => ({
    slot: item.slot ?? item.time ?? "",
    amount: item.amount ?? item.ratio ?? 0,
  }));
  const totalTimeSales = rawTimeSlots.reduce((sum, item) => sum + item.amount, 0);
  const timeSlots = rawTimeSlots.map((item) => ({
    slot: item.slot,
    ratio: item.amount <= 100 ? item.amount : Math.round((item.amount / Math.max(totalTimeSales, 1)) * 100),
  }));

  const ageDistribution = data.charts.age_distribution.map((item) => ({
    age_group: item.age_group ?? item.age ?? "",
    resident: item.resident ?? item.count ?? 0,
    worker: item.worker ?? Math.round((item.count ?? 0) * 0.72),
  }));

  return {
    ...data,
    area_nm: data.area_nm || meta.area_nm || "상권",
    gu_nm: data.gu_nm || meta.gu_nm || "서울시",
    area_type: data.area_type || meta.area_type || "상권",
    charts: {
      sales_trend: salesTrend,
      time_slots: timeSlots,
      age_distribution: ageDistribution,
    },
    summary: {
      monthly_sales_avg: data.summary?.monthly_sales_avg ?? Math.round((salesTrend.at(-1)?.sales ?? 2.3) * 100000000),
      store_count: data.summary?.store_count ?? 147,
      open_rate: data.summary?.open_rate ?? 12.3,
      close_rate: data.summary?.close_rate ?? 8.1,
    },
  } as ReportResponse;
}

async function fetchReport(areaCd: string) {
  const response = await fetch(`${BASE_URL}/api/v1/report/${areaCd}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json() as Promise<ReportResponse>;
}

export default function ReportDetailPage() {
  const params = useParams<{ area_cd: string }>();
  const areaCd = params.area_cd;
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setIsLoading(true);
    fetchReport(areaCd)
      .then((data) => {
        if (alive) setReport(normalizeReport(data, areaCd));
      })
      .catch((event: Error) => {
        if (!alive) return;
        const fallback = normalizeReport(sampleReport(areaCd), areaCd);
        setError(event.message);
        setReport(fallback);
      })
      .finally(() => {
        if (alive) setIsLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [areaCd]);

  useEffect(() => {
    if (!report) return;
    const nextArea = {
      area_cd: areaCd,
      area_nm: report.area_nm,
      gu_nm: report.gu_nm ?? "서울시",
      area_type: report.area_type ?? "상권",
      monthly_sales_avg: report.summary?.monthly_sales_avg,
      risk_score: report.risk_score,
    };
    const current = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]") as typeof nextArea[];
    const next = [nextArea, ...current.filter((item) => item.area_cd !== areaCd)].slice(0, 5);
    localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  }, [areaCd, report]);

  const peakSlot = useMemo(() => {
    const slots = report?.charts.time_slots ?? [];
    return slots.reduce((max, item) => ((item.ratio ?? 0) > (max.ratio ?? 0) ? item : max), slots[0]);
  }, [report]);

  if (isLoading || !report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-golmok-surface">
        <div className="text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-golmok-primary border-t-transparent" />
          <p className="text-sm text-golmok-text-muted">리포트를 불러오는 중입니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-golmok-surface px-4 py-8 pb-24 lg:px-10 lg:py-10">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        {error && (
          <div className="rounded-lg border border-golmok-accent/30 bg-golmok-accent-light/50 px-4 py-3 text-sm text-golmok-text-main">
            백엔드 리포트 응답을 받지 못해 샘플 데이터로 화면을 표시합니다. ({error})
          </div>
        )}

        <header className="grid gap-5 rounded-lg border border-golmok-primary/10 bg-white p-5 shadow-card lg:grid-cols-[1fr_auto]">
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-golmok-primary/10 px-3 py-1 text-sm font-semibold text-golmok-primary">
                {report.area_type}
              </span>
              <span className="text-sm font-medium text-golmok-text-muted">{report.gu_nm}</span>
            </div>
            <div>
              <h1 className="font-display text-3xl font-black text-golmok-text-main sm:text-4xl">
                {report.area_nm} 상권 리포트
              </h1>
              <p className="mt-2 text-sm text-golmok-text-muted">
                공공데이터 기반 매출, 점포, 인구, 정책 정보를 종합해 창업 관점으로 정리했습니다.
              </p>
            </div>
            <Button asChild className="bg-golmok-primary hover:bg-golmok-primary-dark">
              <Link href={`/chat?area=${encodeURIComponent(report.area_nm)}`}>
                <Bot className="mr-2 h-4 w-4" />
                AI에게 이 상권 물어보기
              </Link>
            </Button>
          </div>
          <RiskGauge score={report.risk_score} className="self-center" />
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatCard icon={ReceiptText} label="월평균 매출" value={formatMoney(report.summary?.monthly_sales_avg)} delta={3.8} />
          <StatCard icon={Store} label="점포 수" value={`${report.summary?.store_count ?? 147}개`} delta={1.6} />
          <StatCard icon={Percent} label="개업률" value={`${report.summary?.open_rate?.toFixed(1) ?? "12.3"}%`} delta={0.7} tone="warning" />
          <StatCard icon={Building2} label="폐업률" value={`${report.summary?.close_rate?.toFixed(1) ?? "8.1"}%`} delta={-0.4} tone="danger" />
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
          <ForecastChart areaCd={areaCd} history={report.charts.sales_trend} />
          <RiskDetail areaCd={areaCd} />
        </section>

        <section className="grid gap-5 xl:grid-cols-2">
          <ChartPanel title="매출 트렌드" subtitle="분기별 월평균 매출, 단위: 억원">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={report.charts.sales_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="quarter" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} />
                <Tooltip formatter={(value) => [`${value}억원`, "월평균 매출"]} />
                <Line type="monotone" dataKey="sales" stroke="#2D6A4F" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              </LineChart>
            </ResponsiveContainer>
          </ChartPanel>

          <ChartPanel title="시간대별 매출" subtitle={`피크 시간대: ${peakSlot?.slot ?? "18시"}`}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={report.charts.time_slots}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="slot" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} unit="%" />
                <Tooltip formatter={(value) => [`${value}%`, "매출 비중"]} />
                <Bar dataKey="ratio" fill="#2D6A4F" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartPanel>
        </section>

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <ChartPanel title="인구 구성" subtitle="생활인구와 직장인구 비교">
            <ResponsiveContainer width="100%" height={340}>
              <RadarChart data={report.charts.age_distribution}>
                <PolarGrid />
                <PolarAngleAxis dataKey="age_group" />
                <PolarRadiusAxis angle={30} />
                <Radar name="생활인구" dataKey="resident" stroke="#2D6A4F" fill="#2D6A4F" fillOpacity={0.25} />
                <Radar name="직장인구" dataKey="worker" stroke="#F4A261" fill="#F4A261" fillOpacity={0.22} />
                <Legend />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </ChartPanel>

          <section className="rounded-lg border border-golmok-primary/10 bg-white p-5 shadow-card">
            <div className="mb-4 flex items-center gap-2">
              <Users className="h-5 w-5 text-golmok-primary" />
              <h2 className="text-xl font-black text-golmok-text-main">AI 리포트</h2>
            </div>
            <ReactMarkdown
              components={{
                h2: ({ children }) => <h2 className="mb-2 mt-5 text-xl font-black text-golmok-primary first:mt-0">{children}</h2>,
                p: ({ children }) => <p className="mb-3 leading-7 text-golmok-text-main">{children}</p>,
                li: ({ children }) => <li className="mb-1 leading-7 text-golmok-text-main">{children}</li>,
                ul: ({ children }) => <ul className="mb-3 list-disc pl-5">{children}</ul>,
              }}
            >
              {report.report_md}
            </ReactMarkdown>
          </section>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-black text-golmok-text-main">추천 정책</h2>
          <div className="grid gap-4 md:grid-cols-3">
            {report.matched_policies.slice(0, 3).map((policy, index) => (
              <PolicyCard key={policy.id ?? policy.program_nm ?? index} policy={policy} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function ChartPanel({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-golmok-primary/10 bg-white p-5 shadow-card">
      <div className="mb-4">
        <h2 className="text-xl font-black text-golmok-text-main">{title}</h2>
        <p className="text-sm text-golmok-text-muted">{subtitle}</p>
      </div>
      {children}
    </section>
  );
}

function PolicyCard({ policy }: { policy: ReportPolicy }) {
  const title = policy.program_nm ?? policy.title ?? "추천 지원 정책";
  const amount = policy.budget_max ? `최대 ${policy.budget_max.toLocaleString()}만원` : "지원금액 확인 필요";
  const href = policy.source_url ?? "#";

  return (
    <article className="rounded-lg border border-golmok-primary/10 bg-white p-4 shadow-card">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-golmok-primary">{policy.category ?? "지원사업"}</p>
          <h3 className="mt-1 text-base font-black text-golmok-text-main">{title}</h3>
        </div>
        <span className="rounded-full bg-golmok-risk-low/10 px-2 py-1 text-xs font-bold text-golmok-risk-low">
          추천
        </span>
      </div>
      <p className="text-sm font-semibold text-golmok-text-main">{amount}</p>
      <p className="mt-1 text-sm text-golmok-text-muted">신청기간: {policy.apply_end ?? "상시 또는 공고 확인"}</p>
      {policy.reason && <p className="mt-3 text-sm leading-6 text-golmok-text-muted">{policy.reason}</p>}
      <Button asChild variant="outline" className="mt-4 w-full border-golmok-primary/30 text-golmok-primary hover:bg-golmok-primary/10">
        <Link href={href} target={href === "#" ? undefined : "_blank"} rel="noreferrer">
          신청하기
          <ExternalLink className="ml-2 h-4 w-4" />
        </Link>
      </Button>
    </article>
  );
}
