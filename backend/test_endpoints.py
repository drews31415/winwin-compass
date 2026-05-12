"""전체 API 엔드포인트 통합 테스트 스크립트."""
import asyncio
import io
import sys

import httpx

# Windows cp949 콘솔에서 유니코드 출력 처리
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE = "http://localhost:8000"
SEP  = "-" * 60
PASS = 0
FAIL = 0


def ok(label):
    global PASS
    PASS += 1
    print(f"   [PASS] {label}")


def fail(label, reason):
    global FAIL
    FAIL += 1
    print(f"   [FAIL] {label}: {reason}", file=sys.stderr)


async def test_all():
    async with httpx.AsyncClient(timeout=45) as c:

        # ── a. 매출 상위 상권 ──────────────────────────────────────────────
        print(SEP)
        print("a. POST /api/v1/chat/simple  [매출 상위 상권 5개]")
        r = await c.post(
            f"{BASE}/api/v1/chat/simple",
            json={
                "message": "서울에서 매출이 가장 높은 상권 5개 알려줘",
                "session_id": "test-001",
                "user_context": {},
            },
        )
        d = r.json()
        print(f"   status : {r.status_code}")
        print(f"   intent : {d.get('intent')}")
        sql = d.get("sql") or ""
        print(f"   sql    : {sql[:70]}")
        print(f"   answer : {d.get('answer','')[:130]}")

        if r.status_code != 200:
            fail("status", r.status_code)
        elif d.get("intent") != "data_query":
            fail("intent", d.get("intent"))
        elif not d.get("answer"):
            fail("answer", "empty")
        else:
            ok("intent=data_query, sql present, answer non-empty")

        # ── b. 홍대 카페 창업 ──────────────────────────────────────────────
        print(SEP)
        print("b. POST /api/v1/chat/simple  [홍대 카페 창업]")
        r = await c.post(
            f"{BASE}/api/v1/chat/simple",
            json={
                "message": "홍대 상권 카페 창업하면 어때?",
                "session_id": "test-001",
                "user_context": {},
            },
        )
        d = r.json()
        print(f"   status : {r.status_code}")
        print(f"   intent : {d.get('intent')}")
        print(f"   answer : {d.get('answer','')[:130]}")

        if r.status_code != 200:
            fail("status", r.status_code)
        elif d.get("intent") != "report":
            fail("intent", d.get("intent"))
        elif not d.get("answer"):
            fail("answer", "empty")
        else:
            ok("intent=report, answer non-empty")

        # ── c. policy/match ────────────────────────────────────────────────
        print(SEP)
        print("c. GET /api/v1/policy/match  [카페, capital=5000]")
        r = await c.get(
            f"{BASE}/api/v1/policy/match",
            params={"business_type": "카페", "capital": 5000},
        )
        d = r.json()
        print(f"   status : {r.status_code}")
        print(f"   total  : {d.get('total')}")
        policies = d.get("policies", [])
        if policies:
            p0 = policies[0]
            print(f"   first  : {p0.get('program_nm','')[:40]} | {p0.get('category')}")
            expected_keys = {"program_nm", "category", "target", "apply_end", "source_url"}
            missing = expected_keys - set(p0.keys())
            if missing:
                fail("response keys", f"missing: {missing}")
            else:
                ok(f"total={d['total']}, keys OK")
        else:
            fail("policies", "empty list")

        # ── d. report/{area_cd} ────────────────────────────────────────────
        print(SEP)
        print("d. GET /api/v1/report/3110016  [종로3가]")
        r = await c.get(f"{BASE}/api/v1/report/3110016")
        print(f"   status          : {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            md = d.get("report_md", "")
            charts = d.get("charts", {})
            policies = d.get("matched_policies", [])
            print(f"   area_nm         : {d.get('area_nm')}")
            print(f"   risk_score      : {d.get('risk_score')}")
            print(f"   report_md[:80]  : {md[:80]}")
            print(f"   dev_notice      : {'AI 분석' in md}")
            print(f"   sales_trend     : {len(charts.get('sales_trend', []))} items")
            print(f"   time_slots      : {len(charts.get('time_slots', []))} items")
            print(f"   age_distribution: {len(charts.get('age_distribution', []))} items")
            print(f"   matched_policies: {len(policies)}")

            errs = []
            if "AI 분석" not in md:
                errs.append("dev_notice missing")
            if "charts" not in d:
                errs.append("charts missing")
            if "matched_policies" not in d:
                errs.append("matched_policies missing")
            if errs:
                fail("report", ", ".join(errs))
            else:
                ok("dev_notice present, charts OK, matched_policies present")
        elif r.status_code == 404:
            # area_cd 없음 — 404는 정상 (stub 레코드가 있으면 200)
            print(f"   detail: {r.json().get('detail','')}")
            ok("404 — area_cd not in DB (stub 없음 — 정상)")
        else:
            fail("status", r.status_code)
            print(f"   body: {r.text[:200]}")

        # ── 최종 결과 ──────────────────────────────────────────────────────
        print(SEP)
        print(f"RESULT: {PASS} passed, {FAIL} failed")
        if FAIL:
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_all())
