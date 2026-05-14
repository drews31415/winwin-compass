"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import { useRef } from "react";
import { Compass, MessageSquare, Map, BarChart2, Target, Megaphone } from "lucide-react";
import { cn } from "@/lib/utils";

const SWIPE_THRESHOLD_PX = 48;

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
  const router = useRouter();
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const handledSwipeRef = useRef(false);

  const activeIndex = TAB_ITEMS.findIndex(({ href }) =>
    href === "/"
      ? pathname === "/"
      : pathname === href || pathname.startsWith(href + "/"),
  );

  const navigateBySwipe = (direction: -1 | 1) => {
    if (activeIndex < 0) return;

    const nextIndex = activeIndex + direction;
    const nextTab = TAB_ITEMS[nextIndex];

    if (!nextTab) return;

    handledSwipeRef.current = true;
    router.push(nextTab.href);
  };

  return (
    <nav
      onClickCapture={(event) => {
        if (!handledSwipeRef.current) return;

        event.preventDefault();
        event.stopPropagation();
        handledSwipeRef.current = false;
      }}
      onTouchStart={(event) => {
        const touch = event.touches[0];
        touchStartRef.current = { x: touch.clientX, y: touch.clientY };
        handledSwipeRef.current = false;
      }}
      onTouchEnd={(event) => {
        const touchStart = touchStartRef.current;
        touchStartRef.current = null;

        if (!touchStart) return;

        const touch = event.changedTouches[0];
        const deltaX = touch.clientX - touchStart.x;
        const deltaY = touch.clientY - touchStart.y;

        if (
          Math.abs(deltaX) < SWIPE_THRESHOLD_PX ||
          Math.abs(deltaX) <= Math.abs(deltaY) * 1.2
        ) {
          return;
        }

        navigateBySwipe(deltaX < 0 ? 1 : -1);
      }}
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
