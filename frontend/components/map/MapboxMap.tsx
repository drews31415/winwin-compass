"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import { Layers } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AreaMapFeature } from "@/lib/hooks/useMapData";
import { createMapboxPopupHTML } from "./AreaPopup";

const SEOUL_CENTER: [number, number] = [126.9780, 37.5665];
const TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!;

function toGeoJSON(areas: AreaMapFeature[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: areas.map((a) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [a.lng, a.lat] },
      properties: { ...a },
    })),
  };
}

interface Props {
  areas: AreaMapFeature[];
  selectedArea: AreaMapFeature | null;
  onSelectArea: (area: AreaMapFeature) => void;
}

export default function MapboxMap({ areas, selectedArea, onSelectArea }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef       = useRef<mapboxgl.Map | null>(null);
  const popupRef     = useRef<mapboxgl.Popup | null>(null);
  const [heatmap, setHeatmap] = useState(false);
  const [mapReady, setMapReady] = useState(false);

  // ── 지도 초기화 ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    mapboxgl.accessToken = TOKEN;
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: SEOUL_CENTER,
      zoom: 11,
      localIdeographFontFamily: "'Noto Sans KR', 'Noto Sans CJK KR', sans-serif",
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-right");

    map.on("load", () => {
      // GeoJSON 소스 (클러스터링 활성화)
      map.addSource("areas", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
        cluster: true,
        clusterMaxZoom: 13,
        clusterRadius: 50,
      });

      // 클러스터 원
      map.addLayer({
        id: "clusters",
        type: "circle",
        source: "areas",
        filter: ["has", "point_count"],
        paint: {
          "circle-color": [
            "step", ["get", "point_count"],
            "#B7E4C7", 10, "#52B788", 30, "#2D6A4F",
          ],
          "circle-radius": [
            "step", ["get", "point_count"],
            20, 10, 28, 30, 36,
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#fff",
          "circle-opacity": 0.85,
        },
      });

      // 클러스터 숫자
      map.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "areas",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-size": 13,
          "text-font": ["DIN Offc Pro Medium", "Arial Unicode MS Bold"],
        },
        paint: { "text-color": "#fff" },
      });

      // 개별 마커 (원형, 크기=매출, 색=위험도)
      map.addLayer({
        id: "unclustered-point",
        type: "circle",
        source: "areas",
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-radius": [
            "interpolate", ["linear"],
            ["get", "monthly_sales_avg"],
            0,            6,
            50_000_000,   9,
            150_000_000,  13,
            300_000_000,  17,
          ],
          "circle-color": [
            "case",
            ["<", ["get", "risk_score"], 0.35], "#52B788",
            ["<", ["get", "risk_score"], 0.65], "#F4A261",
            "#E63946",
          ],
          "circle-stroke-width": 2,
          "circle-stroke-color": "#fff",
          "circle-opacity": 0.9,
        },
      });

      // 히트맵 레이어 (기본 숨김)
      map.addLayer(
        {
          id: "heatmap",
          type: "heatmap",
          source: "areas",
          maxzoom: 15,
          layout: { visibility: "none" },
          paint: {
            "heatmap-weight": [
              "interpolate", ["linear"],
              ["get", "monthly_sales_avg"],
              0, 0, 300_000_000, 1,
            ],
            "heatmap-intensity": 1.2,
            "heatmap-color": [
              "interpolate", ["linear"], ["heatmap-density"],
              0,   "rgba(45,106,79,0)",
              0.2, "#B7E4C7",
              0.5, "#F4A261",
              0.8, "#E63946",
              1,   "#9B1B30",
            ],
            "heatmap-radius": 35,
            "heatmap-opacity": 0.8,
          },
        },
        "unclustered-point",
      );

      // 클러스터 클릭 → 줌인
      map.on("click", "clusters", (e) => {
        const features = map.queryRenderedFeatures(e.point, { layers: ["clusters"] });
        const clusterId = features[0].properties!.cluster_id;
        (map.getSource("areas") as mapboxgl.GeoJSONSource).getClusterExpansionZoom(
          clusterId,
          (err, zoom) => {
            if (err || zoom == null) return;
            const coords = (features[0].geometry as GeoJSON.Point).coordinates as [number, number];
            map.easeTo({ center: coords, zoom });
          },
        );
      });

      // 개별 마커 클릭 → 팝업
      map.on("click", "unclustered-point", (e) => {
        if (!e.features?.length) return;
        const props = e.features[0].properties as AreaMapFeature;
        const coords = (e.features[0].geometry as GeoJSON.Point).coordinates as [number, number];

        popupRef.current?.remove();
        popupRef.current = new mapboxgl.Popup({ maxWidth: "280px", offset: 12 })
          .setLngLat(coords)
          .setHTML(createMapboxPopupHTML(props))
          .addTo(map);

        onSelectArea(props);
      });

      // 커서 스타일
      const setCursor = (cursor: string) => () => { map.getCanvas().style.cursor = cursor; };
      map.on("mouseenter", "clusters",           setCursor("pointer"));
      map.on("mouseleave", "clusters",           setCursor(""));
      map.on("mouseenter", "unclustered-point",  setCursor("pointer"));
      map.on("mouseleave", "unclustered-point",  setCursor(""));

      mapRef.current = map;
      setMapReady(true);
    });

    return () => { map.remove(); mapRef.current = null; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── 데이터 업데이트 ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    const src = mapRef.current.getSource("areas") as mapboxgl.GeoJSONSource | undefined;
    src?.setData(toGeoJSON(areas));
  }, [areas, mapReady]);

  // ── 선택 상권으로 이동 ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current || !selectedArea) return;
    mapRef.current.flyTo({
      center: [selectedArea.lng, selectedArea.lat],
      zoom: Math.max(mapRef.current.getZoom(), 14),
      duration: 800,
    });
  }, [selectedArea, mapReady]);

  // ── 히트맵 토글 ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mapReady || !mapRef.current) return;
    mapRef.current.setLayoutProperty(
      "heatmap", "visibility", heatmap ? "visible" : "none",
    );
  }, [heatmap, mapReady]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />

      {/* 히트맵 토글 버튼 */}
      <button
        onClick={() => setHeatmap((v) => !v)}
        className={cn(
          "absolute left-3 top-3 z-10 flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-medium shadow-card",
          "transition-colors",
          heatmap
            ? "border-brand-primary bg-brand-primary text-white"
            : "border-gray-200 bg-white text-gray-600 hover:border-brand-primary/50",
        )}
      >
        <Layers className="h-3.5 w-3.5" />
        히트맵
      </button>

      {/* 범례 */}
      <div className="absolute bottom-8 left-3 z-10 rounded-xl border border-gray-100 bg-white/90 p-3 shadow-card backdrop-blur-sm">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">위험도</p>
        {[
          { color: "#52B788", label: "낮음" },
          { color: "#F4A261", label: "중간" },
          { color: "#E63946", label: "높음" },
        ].map(({ color, label }) => (
          <div key={label} className="mb-1 flex items-center gap-2 last:mb-0">
            <span className="h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-[11px] text-gray-600">{label}</span>
          </div>
        ))}
        <p className="mt-2 text-[10px] text-gray-400">원 크기 = 매출 규모</p>
      </div>
    </div>
  );
}
