"use client";

import { FormEvent, useMemo, useState } from "react";
import { BriefcaseBusiness, Search, Target, WalletCards } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { Toast, type ToastState } from "@/components/ui/Toast";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { PolicyCard } from "@/components/policy/PolicyCard";
import { matchPolicies, searchPolicies, type Policy } from "@/lib/api";

const BUSINESS_TYPES = ["카페", "음식점", "편의점", "미용실", "소매업", "생활서비스"];
const AREAS = ["마포구", "종로구", "성동구", "강남구", "송파구", "용산구", "서대문구"];

const SAMPLE_POLICIES: Policy[] = [
  {
    program_nm: "소상공인 정책자금",
    agency: "중소벤처기업부",
    category: "융자",
    target: "예비창업자 및 소상공인",
    budget_max: 7000,
    apply_end: "2026.06.30",
    source_url: "https://www.semas.or.kr",
    match_score: 0.92,
    reason: "초기 운영자금과 시설자금이 필요한 창업자에게 적합합니다.",
  },
  {
    program_nm: "서울시 청년창업 지원",
    agency: "서울특별시",
    category: "보조금",
    target: "만 39세 이하 예비창업자",
    budget_max: 3000,
    apply_end: "2026.07.31",
    source_url: "https://www.seoul.go.kr",
    match_score: 0.86,
    reason: "청년 창업자의 초기 사업화 비용 부담을 줄이는 데 유리합니다.",
  },
  {
    program_nm: "서울신용보증재단 창업보증",
    agency: "서울신용보증재단",
    category: "보증",
    target: "서울 소재 창업자",
    budget_max: 10000,
    apply_end: "상시",
    source_url: "https://www.seoulshinbo.co.kr",
    match_score: 0.81,
    reason: "담보가 부족한 창업자의 대출 접근성을 높이는 보증 상품입니다.",
  },
];

type FormState = {
  business_type: string;
  area: string;
  capital: string;
  age: string;
};

function normalizePolicies(policies: Policy[]) {
  return policies.length ? policies : SAMPLE_POLICIES;
}

export default function PolicyPage() {
  const [form, setForm] = useState<FormState>({
    business_type: "카페",
    area: "마포구",
    capital: "5000",
    age: "32",
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [policies, setPolicies] = useState<Policy[]>(SAMPLE_POLICIES);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<ToastState>(null);

  const visiblePolicies = useMemo(() => policies, [policies]);

  const updateForm = (key: keyof FormState, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleMatch = async (event?: FormEvent) => {
    event?.preventDefault();
    setIsLoading(true);

    try {
      const result = await matchPolicies({
        business_type: form.business_type,
        area: form.area,
        capital: Number(form.capital) || undefined,
        age: Number(form.age) || undefined,
        is_new: true,
      });
      setPolicies(normalizePolicies(result.policies));
      setToast({ type: "success", message: "맞춤 정책을 찾았습니다." });
    } catch (error) {
      console.error(error);
      setPolicies(SAMPLE_POLICIES);
      setToast({ type: "error", message: "API 응답이 없어 샘플 정책을 표시합니다." });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!searchQuery.trim()) {
      await handleMatch();
      return;
    }

    setIsLoading(true);
    try {
      const result = await searchPolicies(searchQuery.trim());
      setPolicies(normalizePolicies(result.policies));
      setToast({ type: "success", message: "정책 검색이 완료되었습니다." });
    } catch (error) {
      console.error(error);
      const q = searchQuery.trim();
      setPolicies(
        SAMPLE_POLICIES.filter((policy) =>
          [policy.program_nm, policy.category, policy.reason, policy.target]
            .filter(Boolean)
            .some((value) => value!.includes(q)),
        ),
      );
      setToast({ type: "error", message: "API 응답이 없어 샘플 데이터에서 검색했습니다." });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-golmok-surface px-4 py-8 pb-24 lg:px-10 lg:py-10">
        <Toast toast={toast} onClose={() => setToast(null)} />

        <div className="mx-auto flex max-w-7xl flex-col gap-6">
          <header className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-sm font-semibold text-golmok-primary shadow-sm">
              <Target className="h-4 w-4" />
              지원 정책
            </div>
            <div>
              <h1 className="font-display text-3xl font-black text-golmok-text-main sm:text-4xl">
                내 조건에 맞는 창업 지원 정책 찾기
              </h1>
              <p className="mt-2 text-sm text-golmok-text-muted">
                업종, 지역, 예산, 나이를 기준으로 융자, 보조금, 보증, 컨설팅 정책을 추천합니다.
              </p>
            </div>
          </header>

          <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
            <form onSubmit={handleMatch} className="rounded-lg border border-golmok-primary/10 bg-white p-5 shadow-card">
              <div className="mb-5 flex items-center gap-2">
                <BriefcaseBusiness className="h-5 w-5 text-golmok-primary" />
                <h2 className="text-xl font-black text-golmok-text-main">내 상황 입력</h2>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-sm font-semibold text-golmok-text-main">업종</span>
                  <select
                    value={form.business_type}
                    onChange={(event) => updateForm("business_type", event.target.value)}
                    className="h-11 w-full rounded-md border border-input bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-golmok-primary/30"
                  >
                    {BUSINESS_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2">
                  <span className="text-sm font-semibold text-golmok-text-main">지역</span>
                  <select
                    value={form.area}
                    onChange={(event) => updateForm("area", event.target.value)}
                    className="h-11 w-full rounded-md border border-input bg-white px-3 text-sm focus:outline-none focus:ring-2 focus:ring-golmok-primary/30"
                  >
                    {AREAS.map((area) => (
                      <option key={area} value={area}>
                        {area}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2">
                  <span className="text-sm font-semibold text-golmok-text-main">창업 예산</span>
                  <div className="relative">
                    <Input
                      value={form.capital}
                      onChange={(event) => updateForm("capital", event.target.value.replace(/[^0-9]/g, ""))}
                      inputMode="numeric"
                      className="h-11 pr-12"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-golmok-text-muted">만원</span>
                  </div>
                </label>

                <label className="space-y-2">
                  <span className="text-sm font-semibold text-golmok-text-main">나이</span>
                  <div className="relative">
                    <Input
                      value={form.age}
                      onChange={(event) => updateForm("age", event.target.value.replace(/[^0-9]/g, ""))}
                      inputMode="numeric"
                      className="h-11 pr-10"
                    />
                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-golmok-text-muted">세</span>
                  </div>
                </label>
              </div>

              <Button disabled={isLoading} className="mt-5 h-11 w-full bg-golmok-primary hover:bg-golmok-primary-dark">
                <WalletCards className="mr-2 h-4 w-4" />
                {isLoading ? "정책 찾는 중..." : "맞춤 정책 찾기"}
              </Button>
            </form>

            <form onSubmit={handleSearch} className="rounded-lg border border-golmok-primary/10 bg-white p-5 shadow-card">
              <div className="mb-5 flex items-center gap-2">
                <Search className="h-5 w-5 text-golmok-primary" />
                <h2 className="text-xl font-black text-golmok-text-main">정책 검색</h2>
              </div>
              <p className="mb-4 text-sm leading-6 text-golmok-text-muted">
                정책명, 지원 유형, 대상 조건을 직접 입력해 관련 지원사업을 찾아보세요.
              </p>
              <div className="flex gap-2">
                <Input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder="예: 청년 창업 보조금"
                  className="h-11"
                />
                <Button disabled={isLoading} className="h-11 bg-golmok-primary px-5 hover:bg-golmok-primary-dark">
                  검색
                </Button>
              </div>
            </form>
          </section>

          <section className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-xl font-black text-golmok-text-main">추천 정책 카드</h2>
              <span className="text-sm text-golmok-text-muted">{visiblePolicies.length}개</span>
            </div>

            {isLoading ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <CardSkeleton />
                <CardSkeleton />
                <CardSkeleton />
              </div>
            ) : visiblePolicies.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {visiblePolicies.map((policy, index) => (
                  <PolicyCard key={policy.id ?? policy.program_nm ?? index} policy={policy} />
                ))}
              </div>
            ) : (
              <EmptyState description="검색 조건에 맞는 정책이 없습니다. 업종이나 검색어를 바꿔보세요." />
            )}
          </section>
        </div>
      </div>
    </ErrorBoundary>
  );
}
