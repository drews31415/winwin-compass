"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Compass, MessageSquare, Map, BarChart2, Target, Megaphone } from "lucide-react";
import { cn } from "@/lib/utils";

const TAB_ITEMS = [
  { icon: Compass,       label: "홈",       href: "/"       },
  { icon: MessageSquare, label: "AI 상담",  href: "/chat"   },
  { icon: Map,           label: "지도",     href: "/map"    },
  { icon: BarChart2,     label: "리포트",   href: "/report" },
  { icon: Target,        label: "정책",     href: "/policy" },
  { icon: Megaphone,     label: "마케팅",   href: "/marketing" },
] as const;

export function MobileTabBar() {
  const pathname = usePathname();

  return (
    <nav
      className={cn(
        // 모바일 전용 — 데스크톱에서는 Sidebar 사용
        "lg:hidden",
        "fixed bottom-0 inset-x-0 z-40",
        "flex h-[var(--mobile-tabbar-height)] items-stretch border-t border-gray-100 bg-white",
        // 아이폰 홈 인디케이터 영역 확보
        "pb-safe",
      )}
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {TAB_ITEMS.map(({ icon: Icon, label, href }) => {
        const isActive =
          href === "/"
            ? pathname === "/"
            : pathname === href || pathname.startsWith(href + "/");

        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-1 flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors",
              isActive
                ? "text-brand-primary"
                : "text-gray-400 hover:text-gray-600",
            )}
          >
            <Icon
              className={cn(
                "h-5 w-5 transition-colors",
                isActive ? "text-brand-primary" : "text-gray-400",
              )}
              strokeWidth={isActive ? 2.2 : 1.8}
            />
            <span>{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
