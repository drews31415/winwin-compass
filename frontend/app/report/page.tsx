"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { BarChart3, Clock3, Search, Star, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ReportArea = {
  area_cd: string;
  area_nm: string;
  gu_nm: string;
  area_type: string;
  monthly_sales_avg?: number;
  risk_score?: number;
};

const POPULAR_AREAS: ReportArea[] = [
  { area_cd: "3110016", area_nm: "종로3가", gu_nm: "종로구", area_type: "지역상권", monthly_sales_avg: 230000000, risk_score: 58 },
  { area_cd: "3130210", area_nm: "홍대입구", gu_nm: "마포구", area_type: "발달상권", monthly_sales_avg: 410000000, risk_score: 42 },
  { area_cd: "3120190", area_nm: "연남동", gu_nm: "마포구", area_type: "지역상권", monthly_sales_avg: 280000000, risk_score: 49 },
  { area_cd: "3111042", area_nm: "성수역", gu_nm: "성동구", area_type: "발달상권", monthly_sales_avg: 360000000, risk_score: 36 },
  { area_cd: "3130154", area_nm: "신촌역", gu_nm: "서대문구", area_type: "발달상권", monthly_sales_avg: 310000000, risk_score: 61 },
  { area_cd: "3110082", area_nm: "익선동", gu_nm: "종로구", area_type: "지역상권", monthly_sales_avg: 220000000, risk_score: 54 },
  { area_cd: "3120068", area_nm: "이태원역", gu_nm: "용산구", area_type: "관광특구", monthly_sales_avg: 390000000, risk_score: 47 },
  { area_cd: "3140101", area_nm: "강남역", gu_nm: "강남구", area_type: "발달상권", monthly_sales_avg: 520000000, risk_score: 39 },
  { area_cd: "3150088", area_nm: "잠실새내", gu_nm: "송파구", area_type: "지역상권", monthly_sales_avg: 260000000, risk_score: 52 },
  { area_cd: "3120145", area_nm: "망원시장", gu_nm: "마포구", area_type: "전통시장", monthly_sales_avg: 180000000, risk_score: 44 },
];

const RECENT_KEY = "brand-recent-reports";

function formatSales(value?: number) {
  if (!value) return "데이터 준비중";
  return `${(value / 100000000).toFixed(1)}억`;
}

function readRecentAreas(): ReportArea[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]") as ReportArea[];
  } catch {
    return [];
  }
}

export default function ReportPage() {
  const [query, setQuery] = useState("");
  const [recentAreas, setRecentAreas] = useState<ReportArea[]>([]);

  useEffect(() => {
    setRecentAreas(readRecentAreas());
  }, []);

  const filteredAreas = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return POPULAR_AREAS;
    return POPULAR_AREAS.filter((area) =>
      [area.area_nm, area.gu_nm, area.area_type].some((value) => value.toLowerCase().includes(q)),
    );
  }, [query]);

  return (
    <div className="min-h-screen bg-brand-surface px-4 py-8 pb-24 lg:px-10 lg:py-10">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <header className="space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-medium text-brand-primary shadow-sm">
            <BarChart3 className="h-4 w-4" />
            상권 리포트
          </div>
          <div className="space-y-2">
            <h1 className="font-display text-3xl font-bold text-brand-text-main sm:text-4xl">
              분석할 상권을 선택하세요
            </h1>
            <p className="text-base text-brand-text-muted">
              매출 추이, 시간대별 특성, 인구 구성, 위험도와 추천 정책을 한 화면에서 확인합니다.
            </p>
          </div>
        </header>

        <section className="rounded-lg border border-brand-primary/10 bg-white p-4 shadow-card">
          <label className="mb-2 block text-sm font-semibold text-brand-text-main">상권 검색</label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-brand-text-muted" />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="상권명, 자치구, 상권유형을 입력하세요"
              className="h-12 pl-10 text-base"
            />
          </div>
        </section>

        {recentAreas.length > 0 && (
          <section className="space-y-3">
            <div className="flex items-center gap-2">
              <Clock3 className="h-5 w-5 text-brand-primary" />
              <h2 className="text-lg font-bold text-brand-text-main">최근 조회 상권</h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {recentAreas.slice(0, 3).map((area) => (
                <AreaListItem key={area.area_cd} area={area} compact />
              ))}
            </div>
          </section>
        )}

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Star className="h-5 w-5 text-brand-accent" />
              <h2 className="text-lg font-bold text-brand-text-main">인기 상권 TOP 10</h2>
            </div>
            <span className="text-sm text-brand-text-muted">{filteredAreas.length}개 표시</span>
          </div>
          <div className="grid gap-3">
            {filteredAreas.map((area, index) => (
              <AreaListItem key={area.area_cd} area={area} rank={index + 1} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function AreaListItem({ area, rank, compact = false }: { area: ReportArea; rank?: number; compact?: boolean }) {
  return (
    <Link
      href={`/report/${area.area_cd}`}
      className="group grid gap-3 rounded-lg border border-transparent bg-white p-4 shadow-card transition hover:-translate-y-0.5 hover:border-brand-primary/40 hover:shadow-card-hover md:grid-cols-[auto_1fr_auto]"
    >
      {!compact && (
        <div className="flex h-10 w-10 items-center justify-center rounded-md bg-brand-primary/10 text-sm font-bold text-brand-primary">
          {rank}
        </div>
      )}
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-base font-bold text-brand-text-main">{area.area_nm}</h3>
          <span className="rounded-full bg-brand-primary/10 px-2 py-0.5 text-xs font-medium text-brand-primary">
            {area.area_type}
          </span>
        </div>
        <p className="mt-1 text-sm text-brand-text-muted">{area.gu_nm}</p>
      </div>
      <div className="flex items-center justify-between gap-4 md:justify-end">
        <div className="text-right">
          <p className="text-xs text-brand-text-muted">월평균 매출</p>
          <p className="font-bold text-brand-text-main">{formatSales(area.monthly_sales_avg)}</p>
        </div>
        <Button className="bg-brand-primary hover:bg-brand-primary-dark">
          <TrendingUp className="mr-2 h-4 w-4" />
          리포트 보기
        </Button>
      </div>
    </Link>
  );
}
