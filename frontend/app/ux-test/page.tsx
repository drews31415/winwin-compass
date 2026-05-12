"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type UserType = "예비창업자" | "현재 자영업자" | "기타";
type AgeGroup = "20대" | "30대" | "40대" | "50대 이상";

interface SusResponse {
  id: string;
  createdAt: string;
  scores: number[];
  susScore: number;
  grade: string;
  userType: UserType;
  ageGroup: AgeGroup;
  comment: string;
}

const STORAGE_KEY = "sus_responses";

const QUESTIONS = [
  "이 시스템을 자주 사용하고 싶다",
  "이 시스템이 불필요하게 복잡하다",
  "이 시스템을 사용하기 쉬웠다",
  "이 시스템을 사용하려면 전문가의 도움이 필요할 것 같다",
  "이 시스템의 기능들이 잘 통합되어 있다",
  "이 시스템에 일관성이 없다",
  "많은 사람이 이 시스템을 빨리 배울 수 있을 것이다",
  "이 시스템 사용이 매우 불편했다",
  "이 시스템을 사용하는 게 자신 있었다",
  "이 시스템을 사용하기 전에 많은 것을 배워야 한다",
] as const;

const REVERSE_ITEMS = new Set([1, 3, 5, 7, 9]);

function calculateSusScore(scores: number[]) {
  const total = scores.reduce((sum, score, index) => {
    const contribution = REVERSE_ITEMS.has(index) ? 5 - score : score - 1;
    return sum + contribution * 2.5;
  }, 0);
  return Math.round(total);
}

function getGrade(score: number) {
  if (score <= 50) return "나쁨";
  if (score <= 68) return "보통";
  if (score <= 80) return "좋음";
  return "우수";
}

function getStoredResponses(): SusResponse[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveResponses(responses: SusResponse[]) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(responses));
}

function average(values: number[]) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values: number[]) {
  if (values.length < 2) return 0;
  const avg = average(values);
  const variance = average(values.map((value) => (value - avg) ** 2));
  return Math.sqrt(variance);
}

export default function UxTestPage() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [responses, setResponses] = useState<SusResponse[]>([]);
  const [scores, setScores] = useState<number[]>(Array(10).fill(0));
  const [userType, setUserType] = useState<UserType>("예비창업자");
  const [ageGroup, setAgeGroup] = useState<AgeGroup>("30대");
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState<SusResponse | null>(null);

  useEffect(() => {
    setResponses(getStoredResponses());
    setIsAdmin(new URLSearchParams(window.location.search).get("admin") === "1");
  }, []);

  const stats = useMemo(() => {
    const susScores = responses.map((response) => response.susScore);
    const avg = average(susScores);
    return {
      average: Math.round(avg),
      stddev: standardDeviation(susScores).toFixed(1),
      count: responses.length,
      grade: getGrade(Math.round(avg)),
    };
  }, [responses]);

  const questionAverages = useMemo(
    () =>
      QUESTIONS.map((question, index) => ({
        name: `Q${index + 1}`,
        question,
        average: Number(
          average(responses.map((response) => response.scores[index] || 0)).toFixed(2),
        ),
      })),
    [responses],
  );

  const canSubmit = scores.every((score) => score >= 1 && score <= 5);

  function updateScore(index: number, value: number) {
    setScores((current) => current.map((score, idx) => (idx === index ? value : score)));
  }

  function handleSubmit() {
    if (!canSubmit) return;
    const susScore = calculateSusScore(scores);
    const response: SusResponse = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      scores,
      susScore,
      grade: getGrade(susScore),
      userType,
      ageGroup,
      comment: comment.trim(),
    };
    const nextResponses = [...responses, response];
    saveResponses(nextResponses);
    setResponses(nextResponses);
    setSubmitted(response);
  }

  function exportCsv() {
    const header = [
      "id",
      "createdAt",
      "userType",
      "ageGroup",
      ...QUESTIONS.map((_, index) => `Q${index + 1}`),
      "susScore",
      "grade",
      "comment",
    ];
    const rows = responses.map((response) => [
      response.id,
      response.createdAt,
      response.userType,
      response.ageGroup,
      ...response.scores,
      response.susScore,
      response.grade,
      response.comment.replaceAll('"', '""'),
    ]);
    const csv = [header, ...rows]
      .map((row) => row.map((cell) => `"${String(cell)}"`).join(","))
      .join("\n");
    const blob = new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "winwin-compass-sus-responses.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (isAdmin) {
    return (
      <main className="min-h-screen bg-brand-surface px-4 py-8 text-gray-900">
        <div className="mx-auto max-w-6xl">
          <div className="mb-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div>
              <p className="text-sm font-medium text-brand-primary">관리자 뷰</p>
              <h1 className="mt-1 text-3xl font-bold">SUS 응답 분석</h1>
              <p className="mt-2 text-sm text-gray-600">
                이 브라우저의 localStorage에 저장된 사용성 평가 결과입니다.
              </p>
            </div>
            <button
              type="button"
              onClick={exportCsv}
              disabled={!responses.length}
              className="rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              CSV 내보내기
            </button>
          </div>

          <section className="mb-6 grid gap-3 sm:grid-cols-3">
            <Metric label="SUS 평균" value={`${stats.average}점`} />
            <Metric label="표준편차" value={stats.stddev} />
            <Metric label="응답 수" value={`${stats.count}명`} />
          </section>

          <section className="mb-6 rounded-lg border border-gray-200 bg-white p-5">
            <h2 className="mb-4 text-lg font-semibold">문항별 평균 점수</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={questionAverages}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 5]} />
                  <Tooltip
                    formatter={(value) => [`${value}점`, "평균"]}
                    labelFormatter={(label) => {
                      const item = questionAverages.find((entry) => entry.name === label);
                      return item ? `${label}. ${item.question}` : label;
                    }}
                  />
                  <Bar dataKey="average" fill="#2D6A4F" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div className="border-b border-gray-100 px-5 py-4">
              <h2 className="text-lg font-semibold">전체 응답 목록</h2>
            </div>
            {responses.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[900px] text-left text-sm">
                  <thead className="bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3">일시</th>
                      <th className="px-4 py-3">유형</th>
                      <th className="px-4 py-3">연령대</th>
                      <th className="px-4 py-3">SUS</th>
                      <th className="px-4 py-3">등급</th>
                      <th className="px-4 py-3">자유 의견</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {responses.map((response) => (
                      <tr key={response.id}>
                        <td className="px-4 py-3">
                          {new Date(response.createdAt).toLocaleString("ko-KR")}
                        </td>
                        <td className="px-4 py-3">{response.userType}</td>
                        <td className="px-4 py-3">{response.ageGroup}</td>
                        <td className="px-4 py-3 font-semibold">{response.susScore}</td>
                        <td className="px-4 py-3">{response.grade}</td>
                        <td className="max-w-md px-4 py-3 text-gray-600">
                          {response.comment || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="px-5 py-10 text-center text-sm text-gray-500">
                아직 저장된 응답이 없습니다.
              </p>
            )}
          </section>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-brand-surface px-4 py-8 text-gray-900">
      <div className="mx-auto max-w-3xl">
        <section className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
          <p className="text-sm font-medium text-brand-primary">System Usability Scale</p>
          <h1 className="mt-2 text-3xl font-bold">상생나침반 사용성 평가 (SUS 설문)</h1>
          <p className="mt-3 text-sm leading-6 text-gray-600">
            서비스를 직접 사용해보신 후 아래 10문항에 응답해주세요.
          </p>
          <Link
            href="/"
            target="_blank"
            className="mt-4 inline-flex rounded-lg bg-brand-primary px-4 py-2 text-sm font-semibold text-white"
          >
            서비스 이용하기 →
          </Link>
        </section>

        {submitted ? (
          <section className="rounded-lg border border-gray-200 bg-white p-6 text-center">
            <p className="text-sm font-medium text-brand-primary">제출 완료</p>
            <h2 className="mt-2 text-2xl font-bold">
              당신의 사용성 점수: {submitted.susScore}점 ({submitted.grade})
            </h2>
            <p className="mt-3 text-sm text-gray-600">
              현재 평균: {stats.average}점 ({stats.grade}) · N={stats.count}명
            </p>
            <div className="mx-auto mt-6 h-3 max-w-md overflow-hidden rounded-full bg-gray-100">
              <div
                className="h-full rounded-full bg-brand-primary transition-all"
                style={{ width: `${submitted.susScore}%` }}
              />
            </div>
            <div className="mt-6 flex justify-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setScores(Array(10).fill(0));
                  setComment("");
                  setSubmitted(null);
                }}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700"
              >
                새 응답 입력
              </button>
              <Link
                href="/ux-test?admin=1"
                className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white"
              >
                관리자 결과 보기
              </Link>
            </div>
          </section>
        ) : (
          <section className="rounded-lg border border-gray-200 bg-white p-6">
            <div className="mb-5 grid grid-cols-5 gap-2 text-center text-xs text-gray-500">
              <span>1<br />매우 동의 안 함</span>
              <span>2</span>
              <span>3<br />보통</span>
              <span>4</span>
              <span>5<br />매우 동의</span>
            </div>

            <div className="space-y-5">
              {QUESTIONS.map((question, index) => (
                <div key={question} className="rounded-lg border border-gray-100 p-4">
                  <div className="mb-3 flex items-start gap-2">
                    <span className="rounded-md bg-brand-primary/10 px-2 py-1 text-xs font-bold text-brand-primary">
                      Q{index + 1}
                    </span>
                    <p className="font-medium">{question}</p>
                  </div>
                  <div className="grid grid-cols-5 gap-2">
                    {[1, 2, 3, 4, 5].map((value) => (
                      <button
                        key={value}
                        type="button"
                        onClick={() => updateScore(index, value)}
                        className={[
                          "h-11 rounded-lg border text-sm font-semibold transition-colors",
                          scores[index] === value
                            ? "border-brand-primary bg-brand-primary text-white"
                            : "border-gray-200 bg-white text-gray-700 hover:border-brand-primary",
                        ].join(" ")}
                      >
                        {value}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium">
                사용자 유형
                <select
                  value={userType}
                  onChange={(event) => setUserType(event.target.value as UserType)}
                  className="mt-2 w-full rounded-lg border border-gray-200 bg-white px-3 py-2"
                >
                  <option>예비창업자</option>
                  <option>현재 자영업자</option>
                  <option>기타</option>
                </select>
              </label>
              <label className="text-sm font-medium">
                연령대
                <select
                  value={ageGroup}
                  onChange={(event) => setAgeGroup(event.target.value as AgeGroup)}
                  className="mt-2 w-full rounded-lg border border-gray-200 bg-white px-3 py-2"
                >
                  <option>20대</option>
                  <option>30대</option>
                  <option>40대</option>
                  <option>50대 이상</option>
                </select>
              </label>
            </div>

            <label className="mt-4 block text-sm font-medium">
              자유 의견
              <textarea
                value={comment}
                onChange={(event) => setComment(event.target.value)}
                rows={4}
                placeholder="사용하면서 좋았던 점이나 불편했던 점을 적어주세요."
                className="mt-2 w-full resize-none rounded-lg border border-gray-200 px-3 py-2 outline-none focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20"
              />
            </label>

            <button
              type="button"
              onClick={handleSubmit}
              disabled={!canSubmit}
              className="mt-6 w-full rounded-lg bg-brand-primary px-4 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:bg-gray-300"
            >
              제출하고 결과 보기
            </button>
            {!canSubmit && (
              <p className="mt-2 text-center text-xs text-gray-500">
                10개 문항에 모두 응답하면 제출할 수 있습니다.
              </p>
            )}
          </section>
        )}
      </div>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <p className="text-sm text-gray-500">{label}</p>
      <p className="mt-2 text-3xl font-bold text-brand-primary">{value}</p>
    </div>
  );
}
