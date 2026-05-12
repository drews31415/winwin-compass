import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Search } from "lucide-react";
import { StatsCounter } from "@/components/ui/StatsCounter";
import { cn } from "@/lib/utils";

export const metadata: Metadata = {
  title: "상생나침반 — 내 상권, 데이터로 보다",
};

// ── 데이터 ─────────────────────────────────────────────────────────────────────

const EXAMPLE_TAGS = [
  "홍대 카페 창업 분석",
  "마포구 매출 현황",
  "받을 수 있는 지원금",
] as const;

const QUICK_CARDS = [
  {
    emoji: "🔍",
    title: "상권 탐색",
    desc:  "서울 전체 상권 지도에서 내 창업 위치 찾기",
    href:  "/map",
    bg:    "bg-emerald-50",
  },
  {
    emoji: "🤖",
    title: "AI 상담",
    desc:  "창업 고민을 AI에게 물어보세요",
    href:  "/chat",
    bg:    "bg-violet-50",
  },
  {
    emoji: "📈",
    title: "상권 리포트",
    desc:  "특정 상권의 매출·인구·위험도 분석",
    href:  "/report",
    bg:    "bg-blue-50",
  },
  {
    emoji: "💰",
    title: "지원 정책",
    desc:  "나에게 맞는 창업 지원금 찾기",
    href:  "/policy",
    bg:    "bg-amber-50",
  },
] as const;

const STATS = [
  { target: 1600, suffix: "+",  label: "서울시 상권 수"   },
  { target: 3,    suffix: "년", label: "분석 데이터 기간" },
  { target: 50,   suffix: "+개", label: "지원 정책"        },
] as const;

// ── 페이지 ─────────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col bg-brand-surface">

      {/* ── 1. Hero ────────────────────────────────────────────────────────── */}
      <section className="relative flex flex-col items-center px-4 pb-5 pt-7 text-center sm:pb-10 sm:pt-14 lg:pt-24">
        {/* 배경 장식 */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-gradient-to-b from-brand-primary/6 to-transparent"
        />

        {/* 배지 */}
        <span className="relative mb-3 inline-flex items-center gap-1.5 rounded-full border border-brand-primary/20 bg-brand-primary/8 px-3 py-1 text-[11px] font-medium text-brand-primary sm:mb-5 sm:px-4 sm:py-1.5 sm:text-xs">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-primary-light animate-pulse" />
          서울시 공공데이터 기반
        </span>

        <div className="relative mb-3 flex h-24 w-24 items-center justify-center rounded-3xl bg-white shadow-card ring-1 ring-brand-primary/10 sm:mb-5 sm:h-28 sm:w-28 lg:h-24 lg:w-24">
          <Image
            src="/brand/logo.png"
            alt="상생나침반 로고"
            fill
            sizes="(max-width: 640px) 96px, 112px"
            className="object-contain p-2.5"
            priority
          />
        </div>

        {/* 타이틀 */}
        <h1 className="relative mb-2 font-display text-3xl font-bold leading-tight tracking-tight text-brand-text-main sm:mb-4 sm:text-5xl lg:text-6xl">
          내 상권,{" "}
          <span className="text-gradient">데이터로 보다</span>
        </h1>

        {/* 서브타이틀 */}
        <p className="relative mb-5 max-w-md text-sm text-brand-text-muted sm:mb-10 sm:text-lg">
          서울시 공공데이터 기반 지역상권 AI 분석 서비스
        </p>

        {/* 검색창 */}
        <form
          action="/chat"
          method="get"
          className={cn(
            "relative w-full max-w-xl",
            "flex items-center overflow-hidden rounded-2xl",
            "border border-gray-200 bg-white shadow-card",
            "transition-all duration-200",
            "focus-within:border-brand-primary focus-within:shadow-card-hover focus-within:ring-2 focus-within:ring-brand-primary/15",
          )}
        >
          <Search className="ml-3 h-5 w-5 shrink-0 text-gray-400 sm:ml-4" />
          <input
            type="text"
            name="q"
            autoComplete="off"
            placeholder="찾고 싶은 상권이나 질문을 입력하세요"
            className="min-w-0 flex-1 bg-transparent py-3 pl-2 pr-2 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none sm:py-4 sm:pl-3"
          />
          <button
            type="submit"
            className={cn(
              "m-1.5 shrink-0 rounded-xl px-4 py-2.5 sm:px-5",
              "bg-brand-primary text-sm font-medium text-white",
              "transition-colors hover:bg-brand-primary-dark",
              "focus:outline-none focus:ring-2 focus:ring-brand-primary/40",
            )}
          >
            검색
          </button>
        </form>

        {/* 예시 질문 태그 */}
        <div className="relative mt-3 flex flex-wrap justify-center gap-1.5 sm:mt-4 sm:gap-2">
          {EXAMPLE_TAGS.map((tag) => (
            <Link
              key={tag}
              href={`/chat?q=${encodeURIComponent(tag)}`}
              className={cn(
                "rounded-full border border-gray-200 bg-white px-2.5 py-1 sm:px-3.5 sm:py-1.5",
                "text-[11px] text-gray-600 shadow-sm sm:text-xs",
                "transition-all duration-150",
                "hover:border-brand-primary hover:text-brand-primary hover:shadow-card",
              )}
            >
              {tag}
            </Link>
          ))}
        </div>
      </section>

      {/* ── 2. 빠른 시작 카드 ─────────────────────────────────────────────── */}
      <section className="mx-auto w-full max-w-3xl px-4 pb-8 sm:pb-14">
        <h2 className="mb-3 text-center text-base font-semibold text-brand-text-main sm:mb-6 sm:text-lg">
          무엇을 도와드릴까요?
        </h2>

        <div className="grid grid-cols-2 gap-2.5 sm:gap-3">
          {QUICK_CARDS.map((card) => (
            <Link key={card.href} href={card.href} className="group block">
              <div
                className={cn(
                  "flex h-full min-h-[112px] flex-col rounded-2xl border-2 border-gray-100 bg-white p-3 sm:min-h-[180px] sm:p-6",
                  "shadow-card",
                  "transition-all duration-200",
                  "group-hover:border-brand-primary group-hover:-translate-y-1 group-hover:shadow-card-hover",
                )}
              >
                {/* 이모지 아이콘 */}
                <span
                  className={cn(
                    "mb-2 flex h-9 w-9 items-center justify-center rounded-xl text-xl sm:mb-4 sm:h-11 sm:w-11 sm:text-2xl",
                    card.bg,
                  )}
                  role="img"
                  aria-label={card.title}
                >
                  {card.emoji}
                </span>

                <h3 className="mb-1 text-sm font-semibold text-gray-900 transition-colors group-hover:text-brand-primary sm:mb-1.5 sm:text-base">
                  {card.title}
                </h3>
                <p className="text-xs leading-snug text-gray-500 sm:text-sm sm:leading-relaxed">
                  {card.desc}
                </p>

                {/* 화살표 */}
                <span className="mt-auto pt-2 text-[11px] font-medium text-brand-primary-light opacity-100 transition-opacity sm:mt-4 sm:text-xs sm:opacity-0 sm:group-hover:opacity-100">
                  바로가기 →
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── 3. 통계 배너 ──────────────────────────────────────────────────── */}
      <section className="mx-auto hidden w-full max-w-3xl px-4 pb-14 sm:block">
        <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-card">
          <div className="grid grid-cols-3 divide-x divide-gray-100">
            {STATS.map(({ target, suffix, label }) => (
              <div
                key={label}
                className="flex flex-col items-center py-7 text-center"
              >
                <span className="font-display text-3xl font-bold text-brand-primary sm:text-4xl">
                  <StatsCounter target={target} suffix={suffix} />
                </span>
                <span className="mt-1.5 text-xs text-gray-500">{label}</span>
              </div>
            ))}
          </div>

          {/* 하단 캡션 */}
          <div className="border-t border-gray-50 bg-gray-50/60 px-6 py-3 text-center text-xs text-gray-400">
            서울시 열린데이터광장 공공데이터 기반 · 분기별 업데이트
          </div>
        </div>
      </section>

      {/* ── 푸터 ──────────────────────────────────────────────────────────── */}
      <footer className="mt-auto border-t border-gray-100 py-8 text-center text-xs text-gray-400">
        © 2026 상생나침반 &middot; 서울 소상공인을 위한 AI 분석 플랫폼
      </footer>

      {/* 모바일 하단 탭바 여백 */}
      <div className="h-16 lg:hidden" aria-hidden="true" />
    </div>
  );
}
