"""
자연어 질문 → SQL 변환 후 실행.

파이프라인:
  generate_sql() → execute_query() → (오류 시) self_correction() → query()

OPENAI_API_KEY 없으면 dev 모드로 동작 (고정 샘플 쿼리 반환).
"""
import logging
import re
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import TEXT_TO_SQL_PROMPT

logger = logging.getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────────────────────────────

# 위험 DML/DDL 키워드 차단 (단어 경계 매칭으로 substring 오탐 방지)
_DANGEROUS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|EXEC|EXECUTE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)

# LLM 응답에서 ```sql ... ``` / ``` ... ``` 블록 제거
_CODE_BLOCK = re.compile(r"```(?:sql)?\s*|\s*```", re.IGNORECASE)

# API 키 없을 때 사용하는 샘플 쿼리
_DEV_SQL = (
    "SELECT ca.area_nm, sd.year_quarter, sd.industry_nm, "
    "sd.monthly_sales_avg, sd.weekday_sales, sd.weekend_sales "
    "FROM sales_data sd "
    "JOIN commercial_areas ca ON sd.area_cd = ca.area_cd "
    "ORDER BY sd.year_quarter DESC, sd.monthly_sales_avg DESC "
    "LIMIT 10"
)

# 자동 수정 프롬프트
_CORRECTION_PROMPT = """다음 SQL이 오류가 발생했습니다.

원래 질문: {question}
SQL: {sql}
오류: {error}

위 스키마를 참고하여 오류를 수정한 SQL을 작성하세요.
수정된 SQL만 출력하고 설명은 하지 마세요.
"""

# LLM이 이해하기 쉬운 스키마 텍스트 (get_schema_string 반환값)
_SCHEMA_STRING = """테이블: commercial_areas
- area_cd: 상권코드 (예: 3110016)
- area_nm: 상권명 (예: 종로3가)
- gu_nm: 자치구 (예: 종로구)
- area_type: 상권유형 (지역상권/전통시장/발달상권/관광특구)
- geom_lat: 위도
- geom_lng: 경도

테이블: sales_data
- area_cd: 상권코드 (commercial_areas.area_cd 참조)
- industry_cd: 업종코드 (예: CS100001)
- industry_nm: 업종명 (예: 한식음식점)
- year_quarter: 분기 (예: 2024Q3)
- monthly_sales_avg: 월평균매출(원)
- daily_sales_avg: 일평균매출(원)
- weekday_sales: 평일매출(원)
- weekend_sales: 주말매출(원)
- time_slot_sales: 시간대별매출 JSON {"00-06":금액, "06-11":금액, "11-14":금액, "14-17":금액, "17-21":금액, "21-24":금액}

테이블: store_counts
- area_cd: 상권코드
- year_quarter: 분기
- industry_cd: 업종코드
- store_count: 점포수
- open_rate: 개업률(%)
- close_rate: 폐업률(%)

테이블: population_data
- area_cd: 상권코드
- year_quarter: 분기
- total_population: 총생활인구
- age_10s: 10대인구
- age_20s: 20대인구
- age_30s: 30대인구
- age_40s: 40대인구
- age_50s: 50대인구
- age_60s: 60대이상인구
- male_ratio: 남성비율 (0~1)
- female_ratio: 여성비율 (0~1)

테이블: worker_population
- area_cd: 상권코드
- year_quarter: 분기
- total_workers: 총직장인구
- age_20s: 20대직장인
- age_30s: 30대직장인
- age_40s: 40대직장인
- age_50s: 50대직장인

테이블: policy_programs
- program_nm: 사업명
- category: 분류 (융자/보조금/컨설팅/교육)
- target: 지원대상
- budget_min: 최소지원금(원)
- budget_max: 최대지원금(원)
- apply_start: 신청시작일
- apply_end: 신청마감일
- source_url: 상세링크"""


# ── TextToSQLEngine ───────────────────────────────────────────────────────────

class TextToSQLEngine:
    """자연어 질문 → SQL 생성 → DB 실행 → 결과 반환."""

    def __init__(self) -> None:
        from app.core.config import settings
        self._api_key = settings.OPENAI_API_KEY
        self._llm     = None

    # ── LLM 지연 초기화 ───────────────────────────────────────────────────────

    def _get_llm(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=self._api_key,
            )
        return self._llm

    # ── 스키마 ────────────────────────────────────────────────────────────────

    async def get_schema_string(self) -> str:
        """DB 스키마를 LLM이 이해하기 쉬운 텍스트로 반환."""
        return _SCHEMA_STRING

    # ── SQL 생성 ──────────────────────────────────────────────────────────────

    async def generate_sql(self, question: str) -> str:
        """
        자연어 질문 → SQL 생성.

        - TEXT_TO_SQL_PROMPT 사용
        - 응답에서 ```sql 코드블록 파싱
        - 위험 키워드(DROP/DELETE/UPDATE 등) 포함 시 ValueError
        """
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import PromptTemplate

        schema = await self.get_schema_string()
        chain  = (
            PromptTemplate.from_template(TEXT_TO_SQL_PROMPT)
            | self._get_llm()
            | StrOutputParser()
        )
        raw = await chain.ainvoke({"schema": schema, "question": question})
        sql = _CODE_BLOCK.sub("", raw).strip()
        return self._validate(sql)

    # ── 검증 ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _validate(sql: str) -> str:
        """SELECT만 허용. 위험 키워드 발견 시 ValueError."""
        cleaned = sql.strip()
        if _DANGEROUS.search(cleaned):
            raise ValueError(f"허용되지 않는 SQL 키워드 포함: {cleaned[:120]}")
        if not cleaned.upper().startswith("SELECT"):
            raise ValueError(f"SELECT 문만 실행 가능합니다: {cleaned[:80]}")
        return cleaned

    # ── SQL 실행 ──────────────────────────────────────────────────────────────

    async def execute_query(
        self, sql: str, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """
        SQL 실행 후 결과를 dict 리스트로 반환.
        실행 시간은 내부적으로 측정 후 DEBUG 로그에 기록.
        (query() 에서 전체 실행 시간을 ms 단위로 노출)
        """
        t0 = time.monotonic()
        result = await db.execute(text(sql))
        elapsed_ms = int((time.monotonic() - t0) * 1000)

        columns = list(result.keys())
        rows    = [
            {col: val for col, val in zip(columns, row)}
            for row in result.fetchall()
        ]
        logger.debug(
            "execute_query: rows=%d elapsed=%dms sql=%.100s",
            len(rows), elapsed_ms, sql,
        )
        return rows

    # ── 자동 수정 ─────────────────────────────────────────────────────────────

    async def self_correction(
        self, sql: str, error: str, question: str
    ) -> str:
        """
        SQL 오류 시 LLM에게 수정을 요청한다 (호출 1회).

        query() 에서 최대 2회 재시도를 관리하므로 이 메서드는
        단일 수정 시도만 담당한다.
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_core.output_parsers import StrOutputParser

        schema = await self.get_schema_string()
        prompt = (
            f"DB 스키마:\n{schema}\n\n"
            + _CORRECTION_PROMPT.format(
                question=question, sql=sql, error=error
            )
        )
        response = await self._get_llm().ainvoke([
            SystemMessage(content="당신은 PostgreSQL 전문가입니다."),
            HumanMessage(content=prompt),
        ])
        parser  = StrOutputParser()
        raw     = parser.invoke(response)
        fixed   = _CODE_BLOCK.sub("", raw).strip()
        logger.info("self_correction: fixed sql=%.100s", fixed)
        return self._validate(fixed)

    # ── 전체 파이프라인 ───────────────────────────────────────────────────────

    async def query(
        self, question: str, db: AsyncSession
    ) -> dict[str, Any]:
        """
        질문 → SQL → 실행 → (오류 시 최대 2회 자동 수정) → 결과 반환.

        Returns::

            {
                "question":          str,
                "sql":               str,
                "results":           list[dict],
                "execution_time_ms": int,
                "error":             str | None,   # 최종 실패 시에만 존재
            }
        """
        if not self._api_key:
            return await self._dev_query(question, db)

        t_start = time.monotonic()
        sql     = ""
        error   = None

        try:
            sql     = await self.generate_sql(question)
            results = await self.execute_query(sql, db)
            elapsed = int((time.monotonic() - t_start) * 1000)
            logger.info(
                "query OK — rows=%d elapsed=%dms sql=%.80s",
                len(results), elapsed, sql,
            )
            return {
                "question":          question,
                "sql":               sql,
                "results":           results,
                "execution_time_ms": elapsed,
            }

        except Exception as first_exc:
            logger.warning("query attempt 1 failed: %s", first_exc)
            error = str(first_exc)

            # ── 자동 수정 1차 ─────────────────────────────────────────────
            for attempt in range(1, 3):  # 최대 2회 재시도
                try:
                    sql     = await self.self_correction(sql, error, question)
                    results = await self.execute_query(sql, db)
                    elapsed = int((time.monotonic() - t_start) * 1000)
                    logger.info(
                        "query recovered (attempt %d) — rows=%d elapsed=%dms",
                        attempt, len(results), elapsed,
                    )
                    return {
                        "question":          question,
                        "sql":               sql,
                        "results":           results,
                        "execution_time_ms": elapsed,
                    }
                except Exception as retry_exc:
                    logger.warning(
                        "self_correction attempt %d failed: %s", attempt, retry_exc
                    )
                    error = str(retry_exc)

            # 모든 재시도 소진
            elapsed = int((time.monotonic() - t_start) * 1000)
            logger.error("query failed after 2 corrections: %s", error)
            return {
                "question":          question,
                "sql":               sql,
                "results":           [],
                "execution_time_ms": elapsed,
                "error":             error,
            }

    # ── dev 모드 폴백 ─────────────────────────────────────────────────────────

    async def _dev_query(
        self, question: str, db: AsyncSession
    ) -> dict[str, Any]:
        """OPENAI_API_KEY 없을 때 — 고정 샘플 쿼리로 응답."""
        t0 = time.monotonic()
        try:
            results = await self.execute_query(_DEV_SQL, db)
            return {
                "question":          question,
                "sql":               _DEV_SQL,
                "results":           results,
                "execution_time_ms": int((time.monotonic() - t0) * 1000),
            }
        except Exception as exc:
            return {
                "question":          question,
                "sql":               _DEV_SQL,
                "results":           [],
                "execution_time_ms": int((time.monotonic() - t0) * 1000),
                "error":             str(exc),
            }
