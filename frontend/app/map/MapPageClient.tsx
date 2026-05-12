"use client";

import { useMapData } from "@/lib/hooks/useMapData";
import { MapView } from "@/components/map/MapView";
import { MapSidebar } from "@/components/map/MapSidebar";

export function MapPageClient() {
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

  return (
    <div className="flex h-screen overflow-hidden">
      {/* 좌: 필터 + 검색 사이드바 */}
      <MapSidebar
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
    </div>
  );
}
