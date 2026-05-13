"use client";

import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { useMapData } from "@/lib/hooks/useMapData";
import { MapView } from "@/components/map/MapView";
import { MapSidebar } from "@/components/map/MapSidebar";

export function MapPageClient() {
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const {
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
  } = useMapData();

  const activeFilterCount =
    filters.gu_nm.length +
    filters.area_type.length +
    filters.risk_level.length +
    filters.industry.length +
    (filters.search ? 1 : 0);

  return (
    <div className="flex h-[calc(100dvh_-_4rem_-_env(safe-area-inset-bottom))] overflow-hidden lg:h-screen">
      {/* 좌: 필터 + 검색 사이드바 */}
      <MapSidebar
        className="hidden lg:flex"
        filters={filters}
        filteredAreas={filteredAreas}
        guList={guList}
        selectedArea={selectedArea}
        toggleMulti={toggleMulti}
        updateFilter={updateFilter}
        resetFilters={resetFilters}
        onSelectArea={setSelectedArea}
      />

      {/* 우: 지도 */}
      <div className="relative flex-1 overflow-hidden">
        <button
          type="button"
          onClick={() => setMobileFiltersOpen(true)}
          className="absolute left-3 top-3 z-30 inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 shadow-card lg:hidden"
        >
          <SlidersHorizontal className="h-4 w-4 text-brand-primary" />
          필터
          {activeFilterCount > 0 && (
            <span className="rounded-full bg-brand-primary px-1.5 py-0.5 text-[10px] text-white">
              {activeFilterCount}
            </span>
          )}
        </button>

        {isLoading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/80 backdrop-blur-sm">
            <div className="text-center">
              <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-brand-primary border-t-transparent" />
              <p className="text-xs text-gray-500">상권 데이터 불러오는 중...</p>
            </div>
          </div>
        )}

        {error && !isLoading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/90">
            <div className="text-center">
              <p className="mb-1 text-sm font-medium text-red-500">데이터 로드 실패</p>
              <p className="text-xs text-gray-400">{error}</p>
            </div>
          </div>
        )}

        <MapView
          areas={filteredAreas}
          selectedArea={selectedArea}
          onSelectArea={setSelectedArea}
        />
      </div>

      {mobileFiltersOpen && (
        <div className="fixed inset-x-0 top-0 z-50 flex h-[calc(100dvh_-_4rem_-_env(safe-area-inset-bottom))] flex-col bg-black/35 lg:hidden">
          <button
            type="button"
            className="flex-1 cursor-default"
            aria-label="필터 닫기"
            onClick={() => setMobileFiltersOpen(false)}
          />
          <div className="max-h-[78dvh] rounded-t-3xl bg-white shadow-card-hover">
            <MapSidebar
              className="h-full max-h-[78dvh] w-full border-r-0"
              filters={filters}
              filteredAreas={filteredAreas}
              guList={guList}
              selectedArea={selectedArea}
              toggleMulti={toggleMulti}
              updateFilter={updateFilter}
              resetFilters={resetFilters}
              onSelectArea={(area) => {
                setSelectedArea(area);
                setMobileFiltersOpen(false);
              }}
              onClose={() => setMobileFiltersOpen(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
