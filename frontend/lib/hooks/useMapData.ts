"use client";

import { useState, useEffect, useMemo, useCallback } from "react";

export interface AreaMapFeature {
  area_cd: string;
  area_nm: string;
  gu_nm: string;
  area_type: string;
  lat: number;
  lng: number;
  monthly_sales_avg: number;
  store_count: number;
  risk_score: number;
  main_industry: string;
}

export interface MapFilters {
  gu_nm: string[];         // 자치구 멀티셀렉트
  area_type: string[];     // 상권 유형
  risk_level: string[];    // 낮음/중간/높음
  industry: string[];      // 업종
  search: string;
}

export const AREA_TYPES = ["지역상권", "전통시장", "발달상권", "관광특구"] as const;
export const RISK_LEVELS = ["낮음", "중간", "높음"] as const;
export const INDUSTRIES  = ["카페", "음식점", "편의점", "의류", "기타"] as const;

const INITIAL_FILTERS: MapFilters = {
  gu_nm: [],
  area_type: [],
  risk_level: [],
  industry: [],
  search: "",
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const FALLBACK_AREAS: AreaMapFeature[] = [
  {
    area_cd: "3110016",
    area_nm: "종로3가",
    gu_nm: "종로구",
    area_type: "지역상권",
    lat: 37.5704,
    lng: 126.9911,
    monthly_sales_avg: 238_000_000,
    store_count: 154,
    risk_score: 0.52,
    main_industry: "카페",
  },
  {
    area_cd: "2640014",
    area_nm: "마포구 홍대",
    gu_nm: "마포구",
    area_type: "발달상권",
    lat: 37.5563,
    lng: 126.9237,
    monthly_sales_avg: 390_000_000,
    store_count: 188,
    risk_score: 0.72,
    main_industry: "카페",
  },
  {
    area_cd: "3920008",
    area_nm: "은평구 불광동",
    gu_nm: "은평구",
    area_type: "지역상권",
    lat: 37.6105,
    lng: 126.9293,
    monthly_sales_avg: 105_000_000,
    store_count: 83,
    risk_score: 0.28,
    main_industry: "음식점",
  },
  {
    area_cd: "3220005",
    area_nm: "강남역",
    gu_nm: "강남구",
    area_type: "발달상권",
    lat: 37.4979,
    lng: 127.0276,
    monthly_sales_avg: 410_000_000,
    store_count: 312,
    risk_score: 0.22,
    main_industry: "음식점",
  },
  {
    area_cd: "3050004",
    area_nm: "광장시장",
    gu_nm: "종로구",
    area_type: "전통시장",
    lat: 37.5703,
    lng: 126.9978,
    monthly_sales_avg: 83_000_000,
    store_count: 214,
    risk_score: 0.48,
    main_industry: "음식점",
  },
];

function normalizeMapResponse(payload: unknown): AreaMapFeature[] {
  if (Array.isArray(payload)) return payload as AreaMapFeature[];

  if (payload && typeof payload === "object") {
    const value = payload as {
      areas?: unknown;
      data?: unknown;
      results?: unknown;
      area?: {
        area_cd?: string;
        area_nm?: string;
        gu_nm?: string;
        area_type?: string;
        geom_lat?: number;
        geom_lng?: number;
      };
      sales?: Array<{ monthly_sales_avg?: number }>;
      stores?: Array<{ store_count?: number; close_rate?: number }>;
    };

    if (Array.isArray(value.areas)) return value.areas as AreaMapFeature[];
    if (Array.isArray(value.data)) return value.data as AreaMapFeature[];
    if (Array.isArray(value.results)) return value.results as AreaMapFeature[];

    const area = value.area;
    if (
      area &&
      area.area_cd &&
      area.area_cd !== "map" &&
      typeof area.geom_lat === "number" &&
      typeof area.geom_lng === "number"
    ) {
      const closeRate = value.stores?.[0]?.close_rate ?? 0;
      return [{
        area_cd: area.area_cd,
        area_nm: area.area_nm ?? area.area_cd,
        gu_nm: area.gu_nm ?? "",
        area_type: area.area_type ?? "지역상권",
        lat: area.geom_lat,
        lng: area.geom_lng,
        monthly_sales_avg: value.sales?.[0]?.monthly_sales_avg ?? 0,
        store_count: value.stores?.[0]?.store_count ?? 0,
        risk_score: Math.max(0, Math.min(1, closeRate / 20)),
        main_industry: "카페",
      }];
    }
  }

  return FALLBACK_AREAS;
}

function riskLevel(score: number): string {
  if (score < 0.35) return "낮음";
  if (score < 0.65) return "중간";
  return "높음";
}

export function useMapData() {
  const [areas, setAreas]               = useState<AreaMapFeature[]>([]);
  const [isLoading, setIsLoading]       = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [filters, setFilters]           = useState<MapFilters>(INITIAL_FILTERS);
  const [selectedArea, setSelectedArea] = useState<AreaMapFeature | null>(null);

  useEffect(() => {
    setIsLoading(true);
    fetch(`${BASE_URL}/api/v1/areas/map`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<unknown>;
      })
      .then((payload) => {
        setAreas(normalizeMapResponse(payload));
        setError(null);
      })
      .catch((e) => {
        console.warn("Map data fallback:", e);
        setAreas(FALLBACK_AREAS);
        setError(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  // 자치구 목록 (API 응답에서 동적 추출)
  const guList = useMemo(
    () => [...new Set((Array.isArray(areas) ? areas : []).map((a) => a.gu_nm))].sort(),
    [areas],
  );

  const filteredAreas = useMemo(() => {
    return (Array.isArray(areas) ? areas : []).filter((a) => {
      if (filters.gu_nm.length    && !filters.gu_nm.includes(a.gu_nm))         return false;
      if (filters.area_type.length && !filters.area_type.includes(a.area_type)) return false;
      if (filters.industry.length  && !filters.industry.includes(a.main_industry)) return false;
      if (filters.risk_level.length) {
        const lvl = riskLevel(a.risk_score);
        if (!filters.risk_level.includes(lvl)) return false;
      }
      if (filters.search) {
        const q = filters.search.toLowerCase();
        if (!a.area_nm.includes(q) && !a.gu_nm.includes(q)) return false;
      }
      return true;
    });
  }, [areas, filters]);

  const updateFilter = useCallback(
    <K extends keyof MapFilters>(key: K, value: MapFilters[K]) =>
      setFilters((prev) => ({ ...prev, [key]: value })),
    [],
  );

  const toggleMulti = useCallback(
    <K extends "gu_nm" | "area_type" | "risk_level" | "industry">(
      key: K,
      value: string,
    ) => {
      setFilters((prev) => {
        const arr = prev[key] as string[];
        return {
          ...prev,
          [key]: arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value],
        };
      });
    },
    [],
  );

  const resetFilters = useCallback(() => setFilters(INITIAL_FILTERS), []);

  return {
    areas,
    filteredAreas,
    isLoading,
    error,
    filters,
    updateFilter,
    toggleMulti,
    resetFilters,
    guList,
    selectedArea,
    setSelectedArea,
  };
}
