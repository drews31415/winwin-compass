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

export const AREA_TYPES = ["골목상권", "전통시장", "발달상권", "관광특구"] as const;
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
        return r.json() as Promise<AreaMapFeature[]>;
      })
      .then(setAreas)
      .catch((e) => setError(e.message))
      .finally(() => setIsLoading(false));
  }, []);

  // 자치구 목록 (API 응답에서 동적 추출)
  const guList = useMemo(
    () => [...new Set(areas.map((a) => a.gu_nm))].sort(),
    [areas],
  );

  const filteredAreas = useMemo(() => {
    return areas.filter((a) => {
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
