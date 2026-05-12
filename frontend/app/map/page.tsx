import type { Metadata } from "next";
import { MapPageClient } from "./MapPageClient";

export const metadata: Metadata = { title: "상권 지도 — 상생나침반" };

export default function MapPage() {
  return <MapPageClient />;
}
