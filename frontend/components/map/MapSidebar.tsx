"use client";

import { useState, useMemo } from "react";
import { Search, X, ChevronDown, RotateCcw } from "lucide-react";
import { cn } from "@/lib/utils";
import { AreaPopup } from "./AreaPopup";
import {
  AREA_TYPES,
  RISK_LEVELS,
  INDUSTRIES,
  type AreaMapFeature,
  type MapFilters,
} from "@/lib/hooks/useMapData";

// ── 공통 서브 컴포넌트 ────────────────────────────────────────────────────────

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
      {children}
    </p>
  );
}

function ChipGroup({
  options,
  selected,
  onToggle,
}: {
  options: readonly string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const active = selected.includes(opt);
        return (
          <button
            key={opt}
            onClick={() => onToggle(opt)}
            className={cn(
              "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
              active
                ? "border-golmok-primary bg-golmok-primary text-white"
                : "border-gray-200 bg-white text-gray-600 hover:border-golmok-primary/50 hover:text-golmok-primary",
            )}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

function GuDropdown({
  guList,
  selected,
  onToggle,
}: {
  guList: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const label = selected.length === 0 ? "전체 자치구" : `${selected.length}개 선택됨`;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "flex w-full items-center justify-between rounded-xl border px-3 py-2 text-sm transition-colors",
          open
            ? "border-golmok-primary text-golmok-primary"
            : "border-gray-200 text-gray-600 hover:border-gray-300",
        )}
      >
        <span className={cn("text-xs", selected.length ? "font-medium text-golmok-primary" : "")}>
          {label}
        </span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-y-auto rounded-xl border border-gray-100 bg-white shadow-card-hover">
          {guList.map((gu) => (
            <button
              key={gu}
              onClick={() => onToggle(gu)}
              className="flex w-full items-center gap-2 px-3 py-2 text-xs hover:bg-gray-50"
            >
              <span
                className={cn(
                  "h-3.5 w-3.5 shrink-0 rounded border transition-colors",
                  selected.includes(gu)
                    ? "border-golmok-primary bg-golmok-primary"
                    : "border-gray-300",
                )}
              />
              <span className={selected.includes(gu) ? "font-medium text-golmok-primary" : "text-gray-700"}>
                {gu}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── 검색 결과 리스트 ──────────────────────────────────────────────────────────

function AreaList({
  areas,
  selectedArea,
  onSelect,
}: {
  areas: AreaMapFeature[];
  selectedArea: AreaMapFeature | null;
  onSelect: (area: AreaMapFeature) => void;
}) {
  if (areas.length === 0) {
    return (
      <p className="py-6 text-center text-xs text-gray-400">
        검색 결과가 없습니다.
      </p>
    );
  }

  return (
    <div className="space-y-1">
      {areas.slice(0, 50).map((area) => {
        const riskColor =
          area.risk_score < 0.35 ? "bg-emerald-400"
          : area.risk_score < 0.65 ? "bg-amber-400"
          : "bg-red-500";

        return (
          <button
            key={area.area_cd}
            onClick={() => onSelect(area)}
            className={cn(
              "flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left transition-colors",
              selectedArea?.area_cd === area.area_cd
                ? "bg-golmok-primary/8 text-golmok-primary"
                : "hover:bg-gray-50",
            )}
          >
            <span className={cn("h-2 w-2 shrink-0 rounded-full", riskColor)} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-gray-800">{area.area_nm}</p>
              <p className="text-[10px] text-gray-400">{area.gu_nm} · {area.area_type}</p>
            </div>
          </button>
        );
      })}
      {areas.length > 50 && (
        <p className="pt-1 text-center text-[10px] text-gray-400">
          +{areas.length - 50}개 더 있습니다 (필터를 좁혀보세요)
        </p>
      )}
    </div>
  );
}

// ── 메인 사이드바 ─────────────────────────────────────────────────────────────

interface Props {
  filters: MapFilters;
  filteredAreas: AreaMapFeature[];
  guList: string[];
  selectedArea: AreaMapFeature | null;
  toggleMulti: (key: "gu_nm" | "area_type" | "risk_level" | "industry", value: string) => void;
  updateFilter: <K extends keyof MapFilters>(key: K, value: MapFilters[K]) => void;
  resetFilters: () => void;
  onSelectArea: (area: AreaMapFeature) => void;
}

export function MapSidebar({
  filters,
  filteredAreas,
  guList,
  selectedArea,
  toggleMulti,
  updateFilter,
  resetFilters,
  onSelectArea,
}: Props) {
  const hasFilters = useMemo(
    () =>
      filters.gu_nm.length > 0 ||
      filters.area_type.length > 0 ||
      filters.risk_level.length > 0 ||
      filters.industry.length > 0 ||
      filters.search !== "",
    [filters],
  );

  return (
    <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-gray-100 bg-white">
      {/* 헤더 */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <span className="text-sm font-semibold text-golmok-text-main">상권 필터</span>
        {hasFilters && (
          <button
            onClick={resetFilters}
            className="flex items-center gap-1 text-[11px] text-golmok-primary hover:underline"
          >
            <RotateCcw className="h-3 w-3" />
            초기화
          </button>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-5 overflow-y-auto p-4">
        {/* 자치구 */}
        <div>
          <SectionTitle>자치구</SectionTitle>
          <GuDropdown
            guList={guList}
            selected={filters.gu_nm}
            onToggle={(v) => toggleMulti("gu_nm", v)}
          />
        </div>

        {/* 상권 유형 */}
        <div>
          <SectionTitle>상권 유형</SectionTitle>
          <ChipGroup
            options={AREA_TYPES}
            selected={filters.area_type}
            onToggle={(v) => toggleMulti("area_type", v)}
          />
        </div>

        {/* 위험도 */}
        <div>
          <SectionTitle>위험도</SectionTitle>
          <ChipGroup
            options={RISK_LEVELS}
            selected={filters.risk_level}
            onToggle={(v) => toggleMulti("risk_level", v)}
          />
        </div>

        {/* 업종 */}
        <div>
          <SectionTitle>업종</SectionTitle>
          <ChipGroup
            options={INDUSTRIES}
            selected={filters.industry}
            onToggle={(v) => toggleMulti("industry", v)}
          />
        </div>

        {/* 검색창 */}
        <div>
          <SectionTitle>상권 검색</SectionTitle>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={filters.search}
              onChange={(e) => updateFilter("search", e.target.value)}
              placeholder="상권명 또는 자치구"
              className={cn(
                "w-full rounded-xl border border-gray-200 bg-gray-50 py-2 pl-8 pr-8 text-xs",
                "placeholder:text-gray-400 focus:border-golmok-primary focus:bg-white focus:outline-none",
              )}
            />
            {filters.search && (
              <button
                onClick={() => updateFilter("search", "")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        </div>

        {/* 결과 카운트 */}
        <div className="flex items-center justify-between">
          <SectionTitle>검색 결과</SectionTitle>
          <span className="text-[10px] text-golmok-primary">
            {filteredAreas.length}개
          </span>
        </div>

        {/* 결과 리스트 */}
        <AreaList
          areas={filteredAreas}
          selectedArea={selectedArea}
          onSelect={onSelectArea}
        />
      </div>

      {/* 선택된 상권 팝업 (사이드바 하단 고정) */}
      {selectedArea && (
        <div className="border-t border-gray-100 p-3">
          <AreaPopup
            area={selectedArea}
            onClose={() => onSelectArea(selectedArea)}
            compact={false}
          />
        </div>
      )}
    </aside>
  );
}
