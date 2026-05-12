"use client";

import "leaflet/dist/leaflet.css";

import { useEffect } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import type { AreaMapFeature } from "@/lib/hooks/useMapData";
import { AreaPopup, riskColor } from "./AreaPopup";

const SEOUL: [number, number] = [37.5665, 126.9780];

function markerRadius(sales: number): number {
  if (sales >= 300_000_000) return 16;
  if (sales >= 150_000_000) return 12;
  if (sales >= 50_000_000)  return  9;
  return 6;
}

// 선택 상권으로 지도 이동
function FlyToArea({ area }: { area: AreaMapFeature | null }) {
  const map = useMap();
  useEffect(() => {
    if (area) map.flyTo([area.lat, area.lng], 15, { duration: 0.8 });
  }, [area, map]);
  return null;
}

interface Props {
  areas: AreaMapFeature[];
  selectedArea: AreaMapFeature | null;
  onSelectArea: (area: AreaMapFeature) => void;
}

export default function LeafletMap({ areas, selectedArea, onSelectArea }: Props) {
  return (
    <MapContainer
      center={SEOUL}
      zoom={11}
      scrollWheelZoom
      className="h-full w-full"
      style={{ zIndex: 0 }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      <FlyToArea area={selectedArea} />

      {areas.map((area) => (
        <CircleMarker
          key={area.area_cd}
          center={[area.lat, area.lng]}
          radius={markerRadius(area.monthly_sales_avg)}
          pathOptions={{
            color: "#fff",
            fillColor: riskColor(area.risk_score),
            fillOpacity: 0.88,
            weight: 2,
          }}
          eventHandlers={{ click: () => onSelectArea(area) }}
        >
          <Popup maxWidth={280} className="brand-popup">
            <AreaPopup area={area} />
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
