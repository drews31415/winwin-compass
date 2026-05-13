"use client";

import { Compass } from "lucide-react";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "홍대 카페 창업 시 예상 매출은?",
  "강남구 음식점 폐업 위험도 분석",
  "마포구 상권 트렌드 알려줘",
  "소상공인 창업 지원금 받을 수 있어?",
  "이태원 vs 합정, 어디가 더 좋아?",
  "서울 상권 중 성장 가능성 높은 곳은?",
] as const;

interface Props {
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({ onSelect }: Props) {
  return (
    <div className="flex flex-col items-center gap-6 py-8">
      {/* 아이콘 */}
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-primary/10">
        <Compass className="h-8 w-8 text-brand-primary" aria-hidden="true" />
      </div>

      <div className="text-center">
        <h2 className="text-lg font-semibold text-brand-text-main">
          상생나침반 AI에게 물어보세요
        </h2>
        <p className="mt-1 text-sm text-brand-text-muted">
          서울 상권 분석, 지원금 탐색, 창업 상담을 도와드립니다
        </p>
      </div>

      <div className="grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className={cn(
              "rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-700",
              "shadow-sm transition-all duration-150",
              "hover:border-brand-primary hover:text-brand-primary hover:shadow-card",
            )}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
