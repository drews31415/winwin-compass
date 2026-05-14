"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { BarChart3, Clock3, Search, Star, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getAreas, type Area } from "@/lib/api";

type ReportArea = {
  area_cd: string;
  area_nm: string;
  gu_nm: string;
  area_type: string;
};

const RECENT_KEY = "brand-recent-reports";

function readRecentAreas(): ReportArea[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]") as ReportArea[];
  } catch {
    return [];
  }
}

function toReportArea(area: Area): ReportArea {
  return {
    area_cd: area.area_cd,
    area_nm: area.area_nm,
    gu_nm: area.gu_nm,
    area_type: area.area_type,
  };
}

export default function ReportPage() {
  const [query, setQuery] = useState("");
  const [recentAreas, setRecentAreas] = useState<ReportArea[]>([]);
  const [areas, setAreas] = useState<ReportArea[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRecentAreas(readRecentAreas());
  }, []);

  const trimmedQuery = query.trim();

  useEffect(() => {
    let ignore = false;
    const timer = window.setTimeout(() => {
      setIsLoading(true);
      getAreas({ q: trimmedQuery || undefined, limit: 50 })
        .then((result) => {
          if (ignore) return;
          setAreas(result.map(toReportArea));
          setError(null);
        })
        .catch((event: Error) => {
          if (ignore) return;
          setAreas([]);
          setError(event.message);
        })
        .finally(() => {
          if (!ignore) setIsLoading(false);
        });
    }, trimmedQuery ? 250 : 0);

    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [trimmedQuery]);

  const heading = useMemo(() => (trimmedQuery ? "검색 결과" : "수집된 상권"), [trimmedQuery]);

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
              실제 수집 데이터가 있는 상권을 선택하세요
            </h1>
            <p className="text-base text-brand-text-muted">
              검색 결과와 리포트는 DB에 수집된 서울시 상권 데이터만 표시합니다.
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
              placeholder="상권명, 자치구, 상권유형, 상권코드를 입력하세요"
              className="h-12 pl-10 text-base"
            />
          </div>
          {error && (
            <p className="mt-2 text-sm text-red-600">
              실제 상권 데이터를 불러오지 못했습니다. 백엔드 DB 연결과 수집 상태를 확인하세요. ({error})
            </p>
          )}
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
              <h2 className="text-lg font-bold text-brand-text-main">{heading}</h2>
            </div>
            <span className="text-sm text-brand-text-muted">
              {isLoading ? "불러오는 중" : `${areas.length}개 표시`}
            </span>
          </div>

          {!isLoading && areas.length === 0 ? (
            <div className="rounded-lg border border-dashed border-gray-200 bg-white p-8 text-center text-sm text-brand-text-muted">
              표시할 실제 수집 상권 데이터가 없습니다.
            </div>
          ) : (
            <div className="grid gap-3">
              {areas.map((area) => (
                <AreaListItem key={area.area_cd} area={area} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function AreaListItem({ area, compact = false }: { area: ReportArea; compact?: boolean }) {
  return (
    <Link
      href={`/report/${area.area_cd}`}
      className="group grid gap-3 rounded-lg border border-transparent bg-white p-4 shadow-card transition hover:-translate-y-0.5 hover:border-brand-primary/40 hover:shadow-card-hover md:grid-cols-[1fr_auto]"
    >
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="truncate text-base font-bold text-brand-text-main">{area.area_nm}</h3>
          <span className="rounded-full bg-brand-primary/10 px-2 py-0.5 text-xs font-medium text-brand-primary">
            {area.area_type}
          </span>
        </div>
        <p className="mt-1 text-sm text-brand-text-muted">{area.gu_nm}</p>
      </div>
      {!compact && (
        <div className="flex items-center justify-end">
          <Button className="bg-brand-primary hover:bg-brand-primary-dark">
            <TrendingUp className="mr-2 h-4 w-4" />
            리포트 보기
          </Button>
        </div>
      )}
    </Link>
  );
}
