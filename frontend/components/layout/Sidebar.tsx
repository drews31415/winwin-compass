"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Compass,
  MessageSquare,
  Map,
  BarChart2,
  Target,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { icon: MessageSquare, label: "AI 상담",   href: "/chat"     },
  { icon: Map,           label: "상권 지도",  href: "/map"      },
  { icon: BarChart2,     label: "리포트",     href: "/report"   },
  { icon: Target,        label: "지원 정책",  href: "/policy"   },
  { icon: Settings,      label: "설정",       href: "/settings" },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        // 데스크톱 전용 — 모바일에서는 MobileTabBar 사용
        "hidden lg:flex",
        "fixed inset-y-0 left-0 z-40 w-[var(--sidebar-width)] flex-col",
        "bg-white border-r border-gray-100",
      )}
    >
      {/* 로고 */}
      <div className="flex h-16 shrink-0 items-center border-b border-gray-100 px-5">
        <Link href="/" className="group flex items-center gap-2.5">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-golmok-primary transition-colors group-hover:bg-golmok-primary-dark">
            <Compass className="h-4 w-4 text-white" />
          </span>
          <span className="font-display text-base font-bold tracking-tight text-golmok-primary">
            상생나침반
          </span>
        </Link>
      </div>

      {/* 내비게이션 */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map(({ icon: Icon, label, href }) => {
          const isActive =
            pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn("nav-link", isActive && "nav-link-active")}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* 하단 정보 */}
      <div className="shrink-0 border-t border-gray-100 px-5 py-4">
        <p className="text-[11px] leading-relaxed text-gray-400">
          상생나침반 v0.2
          <br />
          서울 소상공인 AI 분석 플랫폼
        </p>
      </div>
    </aside>
  );
}
