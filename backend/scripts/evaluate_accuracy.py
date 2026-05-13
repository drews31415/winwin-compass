"""
AI response accuracy evaluator for contest evidence.

Usage:
  python scripts/evaluate_accuracy.py --url http://localhost:8000 --output EVAL_REPORT.md
  python scripts/evaluate_accuracy.py --url https://winwin-compass-production.up.railway.app
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KeywordSpec = str | list[str]


EVAL_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "Q01",
        "question": "서울에서 카페 매출이 가장 높은 상권 3개 알려줘",
        "intent": "data_query",
        "expected_keywords": ["상권", "매출", ["월평균", "평균", "추정매출"]],
        "should_contain_data": True,
    },
    {
        "id": "Q02",
        "question": "홍대 상권 폐업률이 어떻게 돼?",
        "intent": "data_query",
        "expected_keywords": ["폐업률", "%"],
        "should_contain_data": True,
    },
    {
        "id": "Q03",
        "question": "마포구 카페 창업 분석해줘",
        "intent": "report",
        "expected_keywords": ["매출", "인구", "위험"],
        "should_contain_data": True,
    },
    {
        "id": "Q04",
        "question": "청년 창업 지원금 받을 수 있어?",
        "intent": "policy",
        "expected_keywords": ["지원", ["자금", "지원금"], "신청"],
        "should_contain_data": False,
    },
    {
        "id": "Q05",
        "question": "홍대 vs 신촌 카페 창업 어디가 나아?",
        "intent": "comparison",
        "expected_keywords": ["홍대", "신촌", ["비교", "장점", "단점"]],
        "should_contain_data": True,
    },
    {
        "id": "Q06",
        "question": "종로3가 상권 앞으로 매출 전망이 어때?",
        "intent": "prediction",
        "expected_keywords": [["예측", "전망"], "매출", "분기"],
        "should_contain_data": True,
    },
    {
        "id": "Q07",
        "question": "은평구 불광동 반찬가게 창업 위험해?",
        "intent": "risk_detail",
        "expected_keywords": ["위험", ["요인", "이유", "분석"]],
        "should_contain_data": True,
    },
    {
        "id": "Q08",
        "question": "여성 1인 창업자가 받을 수 있는 정책 추천해줘",
        "intent": "policy",
        "expected_keywords": ["여성", "창업", ["지원", "정책"]],
        "should_contain_data": False,
    },
    {
        "id": "Q09",
        "question": "강남역 음식점 매출 현황 알려줘",
        "intent": "data_query",
        "expected_keywords": ["강남", "음식", "매출"],
        "should_contain_data": True,
    },
    {
        "id": "Q10",
        "question": "종로3가 리포트 만들어줘",
        "intent": "report",
        "expected_keywords": ["종로", ["리포트", "분석"], "위험"],
        "should_contain_data": True,
    },
    {
        "id": "Q11",
        "question": "마포구와 강남구 중 카페 창업 어디가 좋아?",
        "intent": "comparison",
        "expected_keywords": ["마포", "강남", ["비교", "장점", "단점"]],
        "should_contain_data": True,
    },
    {
        "id": "Q12",
        "question": "시니어 창업자가 받을 수 있는 지원사업 있어?",
        "intent": "policy",
        "expected_keywords": ["시니어", ["지원", "정책", "사업"], "창업"],
        "should_contain_data": False,
    },
    {
        "id": "Q13",
        "question": "홍대 상권 내년 매출 예측해줘",
        "intent": "prediction",
        "expected_keywords": ["홍대", ["예측", "전망"], "매출"],
        "should_contain_data": True,
    },
    {
        "id": "Q14",
        "question": "폐업 위험이 높은 이유를 설명해줘",
        "intent": "risk_detail",
        "expected_keywords": ["위험", ["요인", "이유"], ["설명", "분석"]],
        "should_contain_data": True,
    },
    {
        "id": "Q15",
        "question": "서울 전통시장 중 음식점 창업 괜찮은 곳 알려줘",
        "intent": "report",
        "expected_keywords": ["전통시장", "음식", "상권"],
        "should_contain_data": True,
    },
    {
        "id": "Q16",
        "question": "저금리 대출 받을 수 있는 소상공인 정책 찾아줘",
        "intent": "policy",
        "expected_keywords": ["대출", "소상공인", "정책"],
        "should_contain_data": False,
    },
    {
        "id": "Q17",
        "question": "강북구 저자본 카페 추천해줘",
        "intent": "report",
        "expected_keywords": ["강북", "카페", ["추천", "분석"]],
        "should_contain_data": True,
    },
    {
        "id": "Q18",
        "question": "광장시장과 종로3가 상권 비교해줘",
        "intent": "comparison",
        "expected_keywords": ["광장시장", "종로", "비교"],
        "should_contain_data": True,
    },
    {
        "id": "Q19",
        "question": "불광동 상권은 앞으로 좋아질까?",
        "intent": "prediction",
        "expected_keywords": ["불광", ["전망", "예측"], ["향후", "앞으로", "미래"]],
        "should_contain_data": True,
    },
    {
        "id": "Q20",
        "question": "창업 초보인데 어디서부터 보면 돼?",
        "intent": "report",
        "expected_keywords": ["창업", ["상권", "시장"], ["정책", "지원"]],
        "should_contain_data": False,
    },
]


@dataclass
class EvalResult:
    id: str
    question: str
    expected_intent: str
    actual_intent: str
    intent_correct: bool
    keywords_found: bool
    missing_keywords: list[str]
    has_data: bool
    data_expectation_met: bool
    response_time_ms: int
    passed: bool
    answer_preview: str
    error: str | None = None


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    return json.loads(raw)


async def call_chat_api(base_url: str, question: str, timeout: int) -> dict[str, Any]:
    endpoint = f"{base_url.rstrip('/')}/api/v1/chat/simple"
    payload = {
        "message": question,
        "session_id": "accuracy-eval",
        "user_context": {},
    }
    started = time.perf_counter()
    try:
        data = await asyncio.to_thread(_post_json, endpoint, payload, timeout)
        error = None
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, json.JSONDecodeError) as exc:
        data = {"answer": "", "intent": "", "sql": None}
        error = str(exc)
    elapsed = int((time.perf_counter() - started) * 1000)
    data["time_ms"] = elapsed
    data["error"] = error
    return data


def _keyword_matches(answer: str, spec: KeywordSpec) -> bool:
    if isinstance(spec, str):
        return spec in answer
    return any(keyword in answer for keyword in spec)


def _keyword_label(spec: KeywordSpec) -> str:
    if isinstance(spec, str):
        return spec
    return "/".join(spec)


def _contains_data_evidence(answer: str) -> bool:
    data_patterns = [
        r"\d+(\.\d+)?%",
        r"\d{4}년",
        r"\d{4}Q[1-4]",
        r"\d+(\.\d+)?억",
        r"\d+(\.\d+)?점",
        r"\d+(\.\d+)?만원",
        r"\d+분기",
    ]
    return any(re.search(pattern, answer) for pattern in data_patterns)


def evaluate_response(q: dict[str, Any], response: dict[str, Any]) -> EvalResult:
    answer = str(response.get("answer") or "")
    actual_intent = str(response.get("intent") or "")
    missing = [
        _keyword_label(spec)
        for spec in q["expected_keywords"]
        if not _keyword_matches(answer, spec)
    ]
    has_data = bool(response.get("sql")) or _contains_data_evidence(answer)
    should_have_data = bool(q["should_contain_data"])
    data_expectation_met = has_data if should_have_data else True
    intent_correct = actual_intent == q["intent"]
    keywords_found = not missing

    return EvalResult(
        id=q["id"],
        question=q["question"],
        expected_intent=q["intent"],
        actual_intent=actual_intent,
        intent_correct=intent_correct,
        keywords_found=keywords_found,
        missing_keywords=missing,
        has_data=has_data,
        data_expectation_met=data_expectation_met,
        response_time_ms=int(response.get("time_ms") or 0),
        passed=intent_correct and keywords_found and data_expectation_met,
        answer_preview=answer[:120].replace("\n", " "),
        error=response.get("error"),
    )


def make_markdown_report(results: list[EvalResult], base_url: str) -> str:
    total = len(results)
    passed = sum(r.passed for r in results)
    intent_ok = sum(r.intent_correct for r in results)
    keyword_ok = sum(r.keywords_found for r in results)
    data_ok = sum(r.data_expectation_met for r in results)
    avg_time = sum(r.response_time_ms for r in results) / total if total else 0

    lines = [
        "# AI 응답 정확도 평가 리포트",
        "",
        f"- 평가 대상 API: `{base_url.rstrip('/')}/api/v1/chat/simple`",
        f"- 총 질의 수: {total}",
        f"- 통과: {passed}/{total} ({passed / total * 100:.1f}%)",
        f"- 인텐트 분류 정확도: {intent_ok / total * 100:.1f}%",
        f"- 키워드 충족률: {keyword_ok / total * 100:.1f}%",
        f"- 데이터 근거 충족률: {data_ok / total * 100:.1f}%",
        f"- 평균 응답 시간: {avg_time:.0f}ms",
        "",
        "## 질문별 결과",
        "",
        "| ID | Pass | Intent | Expected | Keywords | Data | Time | Question | Preview |",
        "|---|---:|---|---|---|---|---:|---|---|",
    ]
    for r in results:
        pass_mark = "PASS" if r.passed else "FAIL"
        keyword_mark = "OK" if r.keywords_found else f"MISS: {', '.join(r.missing_keywords)}"
        data_mark = "OK" if r.data_expectation_met else "NO DATA"
        preview = r.answer_preview.replace("|", "\\|")
        question = r.question.replace("|", "\\|")
        lines.append(
            f"| {r.id} | {pass_mark} | {r.actual_intent or '-'} | "
            f"{r.expected_intent} | {keyword_mark} | {data_mark} | "
            f"{r.response_time_ms}ms | {question} | {preview} |"
        )

    failed = [r for r in results if not r.passed or r.error]
    if failed:
        lines.extend(["", "## 개선 필요 항목", ""])
        for r in failed:
            lines.append(
                f"- **{r.id}** `{r.question}`: expected `{r.expected_intent}`, "
                f"actual `{r.actual_intent or '-'}`"
            )
            if r.missing_keywords:
                lines.append(f"  - 누락 키워드: {', '.join(r.missing_keywords)}")
            if not r.data_expectation_met:
                lines.append("  - 데이터 근거 부족: 수치, 분기, 비율 등 근거 표현 필요")
            if r.error:
                lines.append(f"  - API 오류: `{r.error}`")

    lines.extend([
        "",
        "## 평가 기준",
        "",
        "- `intent_correct`: API가 반환한 intent와 기대 intent가 일치하는지 확인",
        "- `keywords_found`: 답변 본문에 기대 키워드 또는 동의어 그룹이 포함되는지 확인",
        "- `data_expectation_met`: 데이터형 질문에서 연도, 분기, 비율, 금액, 점수 등 근거 수치가 포함되는지 확인",
        "- 최종 Pass 기준: intent 일치 + 키워드 충족 + 데이터 근거 충족",
        "",
    ])
    return "\n".join(lines)


async def evaluate(base_url: str, output: Path, timeout: int) -> list[EvalResult]:
    results: list[EvalResult] = []
    for q in EVAL_QUESTIONS:
        print(f"[{q['id']}] {q['question']}")
        response = await call_chat_api(base_url, q["question"], timeout)
        result = evaluate_response(q, response)
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(
            f"  {status} intent={result.actual_intent or '-'} "
            f"time={result.response_time_ms}ms"
        )

    total = len(results)
    passed = sum(r.passed for r in results)
    avg_time = sum(r.response_time_ms for r in results) / total if total else 0
    intent_acc = sum(r.intent_correct for r in results) / total * 100 if total else 0

    print("\n=== AI 응답 정확도 평가 결과 ===")
    print(f"총 {total}개 질의 중 {passed}개 통과")
    print(f"정확도: {passed / total * 100:.1f}%")
    print(f"평균 응답 시간: {avg_time:.0f}ms")
    print(f"인텐트 분류 정확도: {intent_acc:.1f}%")

    output.write_text(make_markdown_report(results, base_url), encoding="utf-8")
    print(f"\n리포트 생성: {output}")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate AI chat response accuracy.")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--output", default="EVAL_REPORT.md", help="Markdown output path")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(evaluate(args.url, Path(args.output), args.timeout))


if __name__ == "__main__":
    main()
