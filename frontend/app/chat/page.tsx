"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Plus, MessageSquare, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useChat } from "@/lib/hooks/useChat";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { ChatInput } from "@/components/chat/ChatInput";
import { SuggestedQuestions } from "@/components/chat/SuggestedQuestions";

// ── 컨텍스트 패널 ────────────────────────────────────────────────────────────

function ContextPanel({ onClose }: { onClose?: () => void }) {
  return (
    <aside
      className={cn(
        "hidden w-[280px] shrink-0 flex-col gap-4 border-l border-gray-100 bg-gray-50/60 p-5 xl:flex",
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
          분석 컨텍스트
        </span>
        {onClose && (
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-200"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* 서울 공공데이터 배지 */}
      <div className="rounded-xl border border-brand-primary/20 bg-brand-primary/5 p-4">
        <p className="mb-1 text-xs font-semibold text-brand-primary">데이터 출처</p>
        <p className="text-xs leading-relaxed text-gray-600">
          서울시 열린데이터광장 공공데이터 기반 · 분기별 업데이트
        </p>
      </div>

      {/* 인텐트 설명 */}
      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <p className="mb-3 text-xs font-semibold text-gray-500">AI 분석 유형</p>
        <ul className="space-y-2">
          {[
            { label: "데이터 분석", desc: "매출·인구·업종 통계" },
            { label: "상권 리포트", desc: "위험도·성장성 종합 진단" },
            { label: "지원 정책", desc: "맞춤 지원금 탐색" },
            { label: "상권 비교", desc: "두 지역 상권 비교" },
          ].map(({ label, desc }) => (
            <li key={label} className="flex items-start gap-2">
              <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-primary/60" />
              <span className="text-xs text-gray-600">
                <span className="font-medium text-gray-800">{label}</span> — {desc}
              </span>
            </li>
          ))}
        </ul>
      </div>

      {/* 주의사항 */}
      <div className="mt-auto flex items-start gap-2 rounded-xl bg-amber-50 p-3">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
        <p className="text-[11px] leading-relaxed text-amber-700">
          AI 분석 결과는 참고용입니다. 중요한 결정은 전문가와 상담하세요.
        </p>
      </div>
    </aside>
  );
}

// ── 대화 목록 패널 ───────────────────────────────────────────────────────────

interface SessionPanelProps {
  firstMessage: string | null;
  onNewChat: () => void;
}

function SessionPanel({ firstMessage, onNewChat }: SessionPanelProps) {
  return (
    <aside className="hidden w-[200px] shrink-0 flex-col border-r border-gray-100 bg-gray-50/40 lg:flex">
      <div className="p-3">
        <button
          onClick={onNewChat}
          className={cn(
            "flex w-full items-center gap-2 rounded-xl border border-brand-primary/25 px-3 py-2.5",
            "text-sm font-medium text-brand-primary",
            "transition-colors hover:bg-brand-primary/5",
          )}
        >
          <Plus className="h-4 w-4" />
          새 대화
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        <p className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
          최근 대화
        </p>
        {firstMessage ? (
          <button className="flex w-full items-center gap-2 rounded-lg bg-brand-primary/8 px-2 py-2 text-left">
            <MessageSquare className="h-3.5 w-3.5 shrink-0 text-brand-primary" />
            <span className="truncate text-xs font-medium text-brand-primary">
              {firstMessage}
            </span>
          </button>
        ) : (
          <p className="px-2 text-xs text-gray-400">대화 기록이 없습니다.</p>
        )}
      </div>
    </aside>
  );
}

// ── 메인 채팅 내용 (useSearchParams 사용) ───────────────────────────────────

function ChatContent() {
  const searchParams = useSearchParams();
  const { messages, isLoading, sendMessage, clearMessages } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Home page search query → auto-send once
  const initialQuery = searchParams.get("q");
  const sentInitial = useRef(false);
  useEffect(() => {
    if (initialQuery && !sentInitial.current) {
      sentInitial.current = true;
      sendMessage(initialQuery);
    }
  }, [initialQuery, sendMessage]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const firstUserMsg =
    messages.find((m) => m.role === "user")?.content ?? null;

  const [inputValue, setInputValue] = useState("");

  const handleSend = (text: string) => {
    setInputValue("");
    sendMessage(text);
  };

  const handleSuggest = (q: string) => {
    setInputValue(q);
    sendMessage(q);
  };

  return (
    <div className="fixed inset-x-0 top-0 bottom-[var(--mobile-tabbar-height)] flex overflow-hidden overscroll-none bg-white lg:static lg:h-screen">
      {/* 좌: 대화 목록 */}
      <SessionPanel firstMessage={firstUserMsg} onNewChat={clearMessages} />

      {/* 중: 채팅 영역 */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center border-b border-gray-100 bg-white px-4">
          <h1 className="text-sm font-semibold text-brand-text-main">상생나침반 AI 상담</h1>
          {isLoading && (
            <span className="ml-3 flex items-center gap-1.5 text-xs text-brand-primary">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-primary" />
              분석 중...
            </span>
          )}
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center px-4">
              <SuggestedQuestions onSelect={handleSuggest} />
            </div>
          ) : (
            <ChatWindow messages={messages} />
          )}
        </div>

        <div className="shrink-0 border-t border-gray-100 bg-white px-4 py-3">
          <div className="mx-auto max-w-2xl">
            <ChatInput
              onSend={handleSend}
              disabled={isLoading}
              initialValue={inputValue}
            />
            <p className="mt-2 hidden text-center text-[10px] text-gray-400 sm:block">
              공공 데이터 기반 AI 분석 · 최종 결정은 직접 확인하세요
            </p>
          </div>
        </div>
      </div>

      {/* 우: 컨텍스트 패널 */}
      <ContextPanel />
    </div>
  );
}

// ── 메인 페이지 ─────────────────────────────────────────────────────────────

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center text-sm text-gray-400">로딩 중...</div>}>
      <ChatContent />
    </Suspense>
  );
}
