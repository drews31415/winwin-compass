import type { Metadata, Viewport } from "next";
import { Sidebar } from "@/components/layout/Sidebar";
import { MobileTabBar } from "@/components/layout/MobileTabBar";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default:  "골목 나침반",
    template: "%s | 골목 나침반",
  },
  description: "서울 골목상권 AI 분석 플랫폼 — 소상공인을 위한 맞춤 상권 분석과 정책 안내",
  keywords:    ["골목상권", "소상공인", "창업", "서울", "AI 분석", "상권 분석"],
};

export const viewport: Viewport = {
  width:        "device-width",
  initialScale: 1,
  themeColor:   "#2D6A4F",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="font-sans antialiased bg-background text-foreground">
        {/* 데스크톱: 사이드바 + 콘텐츠 flex 레이아웃 */}
        <div className="flex min-h-screen">
          {/* 사이드바 — lg 이상에서 표시, 240px 고정 */}
          <Sidebar />

          {/* 메인 콘텐츠 — 데스크톱에서 사이드바 너비만큼 오프셋 */}
          <main className="flex min-h-screen w-full flex-col lg:ml-[var(--sidebar-width)]">
            {children}
          </main>
        </div>

        {/* 모바일 하단 탭바 — lg 이하에서 표시 */}
        <MobileTabBar />
      </body>
    </html>
  );
}
