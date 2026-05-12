"use client";

import { FormEvent, useEffect, useState } from "react";
import { CheckCircle2, Clipboard, Megaphone, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Toast, type ToastState } from "@/components/ui/Toast";
import {
  generateMarketing,
  type MarketingGenerateResponse,
  type MarketingPurpose,
  type MarketingTone,
} from "@/lib/api";

const PURPOSES: Array<{ value: MarketingPurpose; label: string }> = [
  { value: "sns", label: "SNS 홍보문" },
  { value: "review", label: "리뷰 답변" },
  { value: "flyer", label: "전단 문구" },
  { value: "menu", label: "메뉴 소개" },
  { value: "event", label: "이벤트 홍보" },
  { value: "pivot", label: "업종전환/리뉴얼" },
];

const TONES: Array<{ value: MarketingTone; label: string }> = [
  { value: "friendly", label: "친근하게" },
  { value: "premium", label: "고급스럽게" },
  { value: "urgent", label: "방문 유도형" },
  { value: "calm", label: "차분하게" },
  { value: "young", label: "젊고 경쾌하게" },
];

type FormState = {
  business_type: string;
  area: string;
  purpose: MarketingPurpose;
  tone: MarketingTone;
  target_customer: string;
  risk_factors: string;
  offer: string;
  menu_items: string;
  extra_context: string;
};

const initialForm: FormState = {
  business_type: "카페",
  area: "마포구",
  purpose: "sns",
  tone: "friendly",
  target_customer: "30대 직장인과 여성 고객",
  risk_factors: "점심 유동인구 감소, 동일 업종 경쟁 과밀",
  offer: "평일 점심 세트 10% 할인",
  menu_items: "아메리카노, 수제 샌드위치, 디카페인 라떼",
  extra_context: "점심 시간대 방문을 회복하고 단골 리뷰를 늘리고 싶습니다.",
};

function splitList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function MarketingPage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<MarketingGenerateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const area = params.get("area");
    const risk = params.get("risk");
    if (area || risk) {
      setForm((prev) => ({
        ...prev,
        area: area ?? prev.area,
        risk_factors: risk ?? prev.risk_factors,
      }));
    }
  }, []);

  const updateForm = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsLoading(true);
    try {
      const data = await generateMarketing({
        business_type: form.business_type,
        area: form.area,
        purpose: form.purpose,
        tone: form.tone,
        target_customer: form.target_customer,
        risk_factors: splitList(form.risk_factors),
        offer: form.offer,
        menu_items: splitList(form.menu_items),
        extra_context: form.extra_context,
      });
      setResult(data);
      setToast({ type: "success", message: "마케팅 문구를 생성했습니다." });
    } catch (error) {
      console.error(error);
      setToast({ type: "error", message: "생성 중 오류가 발생했습니다." });
    } finally {
      setIsLoading(false);
    }
  };

  const copyText = async (text: string) => {
    await navigator.clipboard.writeText(text);
    setToast({ type: "success", message: "문구를 복사했습니다." });
  };

  return (
    <div className="min-h-screen bg-brand-surface px-4 py-8 pb-24 lg:px-10 lg:py-10">
      <Toast toast={toast} onClose={() => setToast(null)} />

      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="space-y-3">
          <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-semibold text-brand-primary shadow-sm">
            <Megaphone className="h-4 w-4" />
            마케팅 자동화
          </div>
          <div>
            <h1 className="font-display text-3xl font-black text-brand-text-main sm:text-4xl">
              위험 진단 이후 바로 쓸 홍보 문구 만들기
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-brand-text-muted">
              폐업 위험 요인과 매장 상황을 바탕으로 SNS, 리뷰 답변, 전단, 메뉴 소개 문구를 생성합니다.
              현재는 텍스트 실행 지원 기능이며, 이미지 보정과 홍보 이미지 생성은 확장 기능입니다.
            </p>
          </div>
        </header>

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <form onSubmit={handleSubmit} className="rounded-lg border border-brand-primary/10 bg-white p-5 shadow-card">
            <div className="mb-5 flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-brand-primary" />
              <h2 className="text-xl font-black text-brand-text-main">생성 조건</h2>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <Field label="업종">
                <Input value={form.business_type} onChange={(event) => updateForm("business_type", event.target.value)} />
              </Field>
              <Field label="지역">
                <Input value={form.area} onChange={(event) => updateForm("area", event.target.value)} />
              </Field>
              <Field label="목적">
                <select
                  value={form.purpose}
                  onChange={(event) => updateForm("purpose", event.target.value as MarketingPurpose)}
                  className="h-10 w-full rounded-md border border-input bg-white px-3 text-sm"
                >
                  {PURPOSES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="톤">
                <select
                  value={form.tone}
                  onChange={(event) => updateForm("tone", event.target.value as MarketingTone)}
                  className="h-10 w-full rounded-md border border-input bg-white px-3 text-sm"
                >
                  {TONES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            <div className="mt-4 space-y-4">
              <Field label="주요 고객">
                <Input value={form.target_customer} onChange={(event) => updateForm("target_customer", event.target.value)} />
              </Field>
              <Field label="위험 요인">
                <Input value={form.risk_factors} onChange={(event) => updateForm("risk_factors", event.target.value)} />
              </Field>
              <Field label="혜택/행사">
                <Input value={form.offer} onChange={(event) => updateForm("offer", event.target.value)} />
              </Field>
              <Field label="대표 메뉴">
                <Input value={form.menu_items} onChange={(event) => updateForm("menu_items", event.target.value)} />
              </Field>
              <label className="block space-y-2">
                <span className="text-sm font-semibold text-brand-text-main">추가 상황</span>
                <textarea
                  value={form.extra_context}
                  onChange={(event) => updateForm("extra_context", event.target.value)}
                  rows={4}
                  className="w-full resize-none rounded-md border border-input bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-primary/30"
                />
              </label>
            </div>

            <Button disabled={isLoading} className="mt-5 h-11 w-full bg-brand-primary hover:bg-brand-primary-dark">
              {isLoading ? "생성 중..." : "마케팅 문구 생성"}
            </Button>
          </form>

          <section className="space-y-4">
            <div className="rounded-lg border border-brand-primary/10 bg-white p-5 shadow-card">
              <h2 className="text-xl font-black text-brand-text-main">생성 결과</h2>
              <p className="mt-2 text-sm text-brand-text-muted">
                생성된 문구는 실제 매장명, 가격, 운영시간을 확인한 뒤 게시하세요.
              </p>
            </div>

            {result ? (
              <>
                {result.source === "sample" && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    OpenAI 응답을 사용할 수 없어 데모용 샘플 문구를 표시합니다.
                  </div>
                )}
                <div className="grid gap-4">
                  {result.contents.map((item, index) => (
                    <article key={`${item.title}-${index}`} className="rounded-lg border border-gray-100 bg-white p-5 shadow-card">
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-semibold uppercase text-brand-primary">{item.channel}</p>
                          <h3 className="mt-1 text-lg font-black text-brand-text-main">{item.title}</h3>
                        </div>
                        <button
                          type="button"
                          onClick={() => copyText(item.content)}
                          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gray-200 text-gray-500 hover:border-brand-primary hover:text-brand-primary"
                          aria-label="복사"
                        >
                          <Clipboard className="h-4 w-4" />
                        </button>
                      </div>
                      <p className="whitespace-pre-line rounded-md bg-gray-50 p-4 text-sm leading-7 text-gray-800">
                        {item.content}
                      </p>
                      <p className="mt-3 text-xs leading-5 text-brand-text-muted">{item.usage_tip}</p>
                    </article>
                  ))}
                </div>
                <div className="rounded-lg border border-brand-primary/10 bg-white p-5 shadow-card">
                  <h3 className="mb-3 text-base font-black text-brand-text-main">실행 체크리스트</h3>
                  <ul className="space-y-2">
                    {result.action_checklist.map((item) => (
                      <li key={item} className="flex gap-2 text-sm text-gray-700">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand-primary" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : (
              <div className="rounded-lg border border-dashed border-gray-200 bg-white p-10 text-center text-sm text-brand-text-muted">
                생성 조건을 확인한 뒤 마케팅 문구를 만들어보세요.
              </div>
            )}
          </section>
        </section>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-sm font-semibold text-brand-text-main">{label}</span>
      {children}
    </label>
  );
}
