"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

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
  gu_nm: string[];
  area_type: string[];
  risk_level: string[];
  industry: string[];
  search: string;
}

export const AREA_TYPES = ["지역상권", "전통시장", "발달상권", "관광특구"] as const;
export const RISK_LEVELS = ["낮음", "중간", "높음"] as const;
export const INDUSTRIES = ["카페", "음식점", "편의점", "의류", "기타"] as const;

const INITIAL_FILTERS: MapFilters = {
  gu_nm: [],
  area_type: [],
  risk_level: [],
  industry: [],
  search: "",
};

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function normalizeMapResponse(payload: unknown): AreaMapFeature[] {
  if (!Array.isArray(payload)) return [];
  return payload.map((area) => {
    const value = area as Partial<AreaMapFeature>;
    return {
      area_cd: String(value.area_cd ?? ""),
      area_nm: String(value.area_nm ?? ""),
      gu_nm: String(value.gu_nm ?? ""),
      area_type: String(value.area_type ?? ""),
      lat: Number(value.lat ?? 0),
      lng: Number(value.lng ?? 0),
      monthly_sales_avg: Number(value.monthly_sales_avg ?? 0),
      store_count: Number(value.store_count ?? 0),
      risk_score: Number(value.risk_score ?? 0),
      main_industry: String(value.main_industry ?? "기타"),
    };
  }).filter((area) => area.area_cd && area.area_nm && area.lat && area.lng);
}

function riskLevel(score: number): string {
  if (score < 0.35) return "낮음";
  if (score < 0.65) return "중간";
  return "높음";
}

export function useMapData() {
  const [areas, setAreas] = useState<AreaMapFeature[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<MapFilters>(INITIAL_FILTERS);
  const [selectedArea, setSelectedArea] = useState<AreaMapFeature | null>(null);

  useEffect(() => {
    let alive = true;
    setIsLoading(true);
    fetch(`${BASE_URL}/api/v1/areas/map`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<unknown>;
      })
      .then((payload) => {
        if (!alive) return;
        setAreas(normalizeMapResponse(payload));
        setError(null);
      })
      .catch((event: Error) => {
        if (!alive) return;
        setAreas([]);
        setError(event.message);
      })
      .finally(() => {
        if (alive) setIsLoading(false);
      });

    return () => {
      alive = false;
    };
  }, []);

  const guList = useMemo(
    () => [...new Set(areas.map((area) => area.gu_nm).filter(Boolean))].sort(),
    [areas],
  );

  const filteredAreas = useMemo(() => {
    return areas.filter((area) => {
      if (filters.gu_nm.length && !filters.gu_nm.includes(area.gu_nm)) return false;
      if (filters.area_type.length && !filters.area_type.includes(area.area_type)) return false;
      if (filters.industry.length && !filters.industry.includes(area.main_industry)) return false;
      if (filters.risk_level.length && !filters.risk_level.includes(riskLevel(area.risk_score))) return false;
      if (filters.search) {
        const q = filters.search.toLowerCase();
        if (!area.area_nm.toLowerCase().includes(q) && !area.gu_nm.toLowerCase().includes(q)) return false;
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
    <K extends "gu_nm" | "area_type" | "risk_level" | "industry">(key: K, value: string) => {
      setFilters((prev) => {
        const arr = prev[key] as string[];
        return {
          ...prev,
          [key]: arr.includes(value) ? arr.filter((item) => item !== value) : [...arr, value],
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
