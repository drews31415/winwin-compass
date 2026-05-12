"use client";

import dynamic from "next/dynamic";
import type { AreaMapFeature } from "@/lib/hooks/useMapData";

const TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
const hasToken = !!TOKEN && TOKEN.startsWith("pk.");

const MapboxMap = hasToken
  ? dynamic(() => import("./MapboxMap"), {
      ssr: false,
      loading: () => <MapLoading label="Mapbox 지도 로딩 중..." />,
    })
  : null;

const LeafletMap = !hasToken
  ? dynamic(() => import("./LeafletMap"), {
      ssr: false,
      loading: () => <MapLoading label="OpenStreetMap 로딩 중..." />,
    })
  : null;

function MapLoading({ label }: { label: string }) {
  return (
    <div className="flex h-full w-full items-center justify-center bg-gray-50">
      <div className="text-center">
        <div className="mx-auto mb-3 h-8 w-8 animate-spin rounded-full border-2 border-golmok-primary border-t-transparent" />
        <p className="text-xs text-gray-400">{label}</p>
      </div>
    </div>
  );
}

interface Props {
  areas: AreaMapFeature[];
  selectedArea: AreaMapFeature | null;
  onSelectArea: (area: AreaMapFeature) => void;
}

export function MapView({ areas, selectedArea, onSelectArea }: Props) {
  if (hasToken && MapboxMap) {
    return (
      <MapboxMap areas={areas} selectedArea={selectedArea} onSelectArea={onSelectArea} />
    );
  }

  if (LeafletMap) {
    return (
      <LeafletMap areas={areas} selectedArea={selectedArea} onSelectArea={onSelectArea} />
    );
  }

  return null;
}
