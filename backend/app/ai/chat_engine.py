"""
WinwinChatEngine — 전체 대화 흐름 관리.

흐름:
  1. Redis에서 대화 이력 로드 (최근 10턴)
  2. classify_intent: keyword → LLM fallback
  3. handle_*: 의도별 컨텍스트 수집 (SQL / RAG / DB)
  4. gpt-4o astream → SSE chunk yield
  5. Redis에 대화 이력 저장 (session_id 키)
"""
import json
import logging
import asyncio
import re
from typing import Any, AsyncGenerator

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.prompts import REPORT_PROMPT, SYSTEM_PROMPT
from app.ai.rag_engine import PolicyRAGEngine
from app.ai.text_to_sql import TextToSQLEngine
from app.ml.forecaster import SalesForecaster
from app.ml.risk_scorer import RiskScorer

logger = logging.getLogger(__name__)

_DEV_NOTICE = (
    "> **AI 분석 기능을 사용하려면 OpenAI API 키가 필요합니다.**  \n"
    "> 현재는 샘플 데이터를 표시합니다.\n\n"
)

# ── 의도 분류 ──────────────────────────────────────────────────────────────────

_INTENT_PROMPT = """사용자 메시지의 의도를 분류하세요. 반드시 아래 중 하나만 출력하세요:
data_query   - 상권 매출·점포·인구 데이터 조회 ("종로3가 매출", "폐업률", "몇 개")
report       - 특정 상권·지역 종합 분석·창업 검토 요청
policy       - 정책·지원금·융자·보조금·혜택 질문
comparison   - 두 상권·지역 비교 ("홍대 vs 신촌", "어디가 나아")
prediction   - 향후 매출 전망·예측 질문
risk_detail  - 폐업 위험도·위기 요인 상세 질문
general      - 그 외 일반 대화

메시지: {message}
의도:"""

# 키워드 매핑 — comparison/policy 우선 판정
_INTENT_KEYWORDS: dict[str, set[str]] = {
    "comparison": {"vs", "VS", "비교", "대비", "어디가", "더 나"},
    "policy":     {"정책", "지원금", "융자", "보조금", "혜택", "신청", "컨설팅", "교육", "대출"},
    "prediction": {"앞으로", "전망", "예측", "될 것 같아", "향후", "미래", "내년"},
    "risk_detail": {"위험", "폐업", "망할", "괜찮아", "리스크", "위기"},
    "report":     {"분석", "리포트", "창업", "어때", "괜찮아", "어떤가", "검토"},
    "data_query": {"매출", "점포", "인구", "폐업률", "개업률", "몇", "얼마", "시간대", "요일", "분기"},
}

_HISTORY_TTL = 60 * 60 * 2   # 2시간
_MAX_TURNS   = 10             # ConversationBufferWindowMemory k=10


class ConversationBufferWindowMemory:
    """LangChain 1.x 호환 인메모리 윈도우 메모리 (Redis 저장 보조용)."""

    def __init__(self, k: int = 5, return_messages: bool = True) -> None:
        self.k               = k
        self.return_messages = return_messages


# ── WinwinChatEngine ───────────────────────────────────────────────────────────

class WinwinChatEngine:
    """사용자 메시지 → 의도 분류 → 데이터 수집 → gpt-4o 스트리밍 응답."""

    def __init__(self) -> None:
        from app.core.config import settings

        self._api_key   = settings.OPENAI_API_KEY
        self._redis_url = settings.REDIS_URL
        self._sql       = TextToSQLEngine()
        self._rag       = PolicyRAGEngine()
        self._risk      = RiskScorer()
        self._forecast  = SalesForecaster()
        self._memory    = ConversationBufferWindowMemory(k=_MAX_TURNS, return_messages=True)
        self._llm: Any  = None   # gpt-4o  (최종 응답)
        self._mini: Any = None   # gpt-4o-mini (분류·보조)
        self._redis: Any = None  # 지연 초기화

    # ── 지연 초기화 ───────────────────────────────────────────────────────────

    def _get_llm(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.3,
                api_key=self._api_key,
                streaming=True,
            )
        return self._llm

    def _get_mini(self):
        if self._mini is None:
            from langchain_openai import ChatOpenAI
            self._mini = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
                api_key=self._api_key,
            )
        return self._mini

    async def _get_redis(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    # ── 대화 이력 (Redis) ─────────────────────────────────────────────────────

    async def _load_history(self, session_id: str) -> list[dict]:
        """Redis에서 최근 k턴 대화 이력 로드."""
        try:
            r   = await self._get_redis()
            raw = await r.get(f"chat:{session_id}")
            if raw:
                return json.loads(raw)[-(_MAX_TURNS * 2):]
        except Exception as exc:
            logger.warning("history load failed: %s", exc)
        return []

    async def _save_history(
        self,
        session_id: str,
        history:    list[dict],
        human:      str,
        ai:         str,
    ) -> None:
        """이번 턴 추가 후 Redis 저장."""
        try:
            trimmed = history[-(_MAX_TURNS * 2 - 2):]
            trimmed.extend([
                {"role": "human", "content": human},
                {"role": "ai",    "content": ai},
            ])
            r = await self._get_redis()
            await r.setex(
                f"chat:{session_id}",
                _HISTORY_TTL,
                json.dumps(trimmed, ensure_ascii=False),
            )
        except Exception as exc:
            logger.warning("history save failed: %s", exc)

    @staticmethod
    def _history_to_messages(history: list[dict]):
        from langchain_core.messages import AIMessage, HumanMessage
        msgs = []
        for h in history:
            if h["role"] == "human":
                msgs.append(HumanMessage(content=h["content"]))
            else:
                msgs.append(AIMessage(content=h["content"]))
        return msgs

    # ── 의도 분류 ─────────────────────────────────────────────────────────────

    async def classify_intent(self, message: str) -> str:
        """
        사용자 의도 분류.

        Returns: "data_query" | "report" | "policy" | "comparison" | "prediction" | "risk_detail" | "general"
        """
        # 우선순위 순 keyword 빠른 판정
        for intent in ("comparison", "policy", "prediction", "risk_detail", "report", "data_query"):
            if any(kw in message for kw in _INTENT_KEYWORDS[intent]):
                return intent

        # LLM fallback (API 키 있을 때만)
        if not self._api_key:
            return "general"

        try:
            from langchain_core.messages import HumanMessage
            from langchain_core.output_parsers import StrOutputParser

            resp   = await self._get_mini().ainvoke(
                [HumanMessage(content=_INTENT_PROMPT.format(message=message))]
            )
            intent = StrOutputParser().invoke(resp).strip().lower()
            valid  = {"data_query", "report", "policy", "comparison", "prediction", "risk_detail", "general"}
            return intent if intent in valid else "general"
        except Exception as exc:
            logger.warning("classify_intent LLM failed: %s", exc)
            return "general"

    # ── 핸들러 ────────────────────────────────────────────────────────────────

    async def handle_data_query(self, message: str, db: AsyncSession) -> str:
        """자연어 → SQL → DB 실행 → LLM 자연어 답변."""
        result = await self._sql.query(message, db)

        if result.get("error") or not result.get("results"):
            return (
                "죄송합니다. 해당 데이터를 조회하지 못했습니다. "
                "상권명을 좀 더 구체적으로 입력해 주시겠어요?"
            )

        rows    = result["results"][:10]
        columns = list(rows[0].keys())
        header  = " | ".join(columns)
        sep     = "-" * len(header)
        table   = "\n".join(
            [header, sep]
            + [
                " | ".join(str(v) if v is not None else "-" for v in row.values())
                for row in rows
            ]
        )

        if not self._api_key:
            return f"[조회 결과]\n{table}"

        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            f"다음은 사용자 질문에 대한 DB 조회 결과입니다.\n\n"
            f"질문: {message}\n\n"
            f"데이터:\n{table}\n\n"
            "위 데이터를 바탕으로 2~3문장의 자연스러운 한국어 답변을 작성하세요. "
            "수치는 구체적으로(예: **2억 3천만원**), 분기 기준을 명시하세요."
        )
        resp = await self._get_mini().ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
        )
        return resp.content

    async def handle_report(self, message: str, db: AsyncSession) -> str:
        """상권 종합 리포트 생성 (DB 조회 + REPORT_PROMPT + LLM)."""
        from app.data.processors.transformer import calculate_risk_score
        from app.models.database import (
            CommercialArea, PopulationData, SalesData, StoreCount,
        )

        area_nm = await self._extract_area(message)

        area_row = (await db.execute(
            select(CommercialArea)
            .where(CommercialArea.area_nm.ilike(f"%{area_nm}%"))
            .limit(1)
        )).scalars().first()

        if not area_row:
            return f"'{area_nm}' 상권 정보를 찾을 수 없습니다. 정확한 상권명을 입력해 주세요."

        area_cd = area_row.area_cd
        area_nm = area_row.area_nm

        latest_q = (await db.execute(
            select(func.max(SalesData.year_quarter))
            .where(SalesData.area_cd == area_cd)
        )).scalar() or (await db.execute(
            select(func.max(StoreCount.year_quarter))
            .where(StoreCount.area_cd == area_cd)
        )).scalar()

        if not latest_q:
            return f"{area_nm} 상권의 데이터가 아직 수집되지 않았습니다."

        sales_rows = (await db.execute(
            select(SalesData)
            .where(SalesData.area_cd == area_cd, SalesData.year_quarter == latest_q)
            .limit(5)
        )).scalars().all()

        store_rows = (await db.execute(
            select(StoreCount)
            .where(StoreCount.area_cd == area_cd, StoreCount.year_quarter == latest_q)
            .limit(5)
        )).scalars().all()

        pop_row = (await db.execute(
            select(PopulationData)
            .where(PopulationData.area_cd == area_cd, PopulationData.year_quarter == latest_q)
            .limit(1)
        )).scalars().first()

        store_dict = {"close_rate": store_rows[0].close_rate if store_rows else 0}
        sales_dict = {"monthly_sales_avg": sales_rows[0].monthly_sales_avg if sales_rows else 0}
        risk_score = calculate_risk_score(store_dict, sales_dict)

        ml_risk, forecast = await asyncio.gather(
            self._score_area_with_new_session(area_cd),
            self._forecast_area_with_new_session(area_cd, periods=4),
            return_exceptions=True,
        )
        ml_risk_text = self._format_risk_result(ml_risk) if not isinstance(ml_risk, Exception) else "ML 위험도 분석 실패"
        forecast_text = self._format_forecast_result(forecast) if not isinstance(forecast, Exception) else "매출 예측 실패"

        def _fmt_sales(rows) -> str:
            if not rows:
                return "데이터 없음"
            return "\n".join(
                f"- {r.industry_nm}: 월평균 {r.monthly_sales_avg:,}원"
                if r.monthly_sales_avg else f"- {r.industry_nm}"
                for r in rows[:3]
            )

        def _fmt_stores(rows) -> str:
            if not rows:
                return "데이터 없음"
            return "\n".join(
                f"- {r.industry_cd}: 점포 {r.store_count}개, 폐업률 {r.close_rate:.1f}%"
                if r.store_count else f"- {r.industry_cd}"
                for r in rows[:3]
            )

        def _fmt_pop(r) -> str:
            if not r or not r.total_population:
                return "데이터 없음"
            return (
                f"총 {r.total_population:,}명 | "
                f"20대 {r.age_20s:,} / 30대 {r.age_30s:,} / 40대 {r.age_40s:,}"
            )

        context = REPORT_PROMPT.format(
            area_nm=area_nm,
            sales_data=_fmt_sales(sales_rows),
            store_data=_fmt_stores(store_rows),
            population_data=_fmt_pop(pop_row),
            risk_score=round(risk_score, 1),
        )
        context += (
            "\n\n## ML 위험도 상세\n"
            f"{ml_risk_text}\n\n"
            "## 향후 4분기 매출 예측\n"
            f"{forecast_text}\n"
        )

        if not self._api_key:
            return f"[DEV 모드]\n{context}"

        from langchain_core.messages import HumanMessage, SystemMessage

        resp = await self._get_mini().ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=context)]
        )
        return resp.content

    async def handle_prediction(self, message: str, db: AsyncSession) -> str:
        """예측 질문 처리."""
        area = await self._resolve_area(message, db)
        if not area:
            return "예측할 상권명을 찾지 못했습니다. 예: '홍대 상권 앞으로 매출 전망 알려줘'"

        try:
            forecast = await self._forecast.predict(area["area_cd"], periods=4, db=db)
        except Exception as exc:
            logger.warning("forecast failed: %s", exc)
            forecast = self._fallback_forecast_result(area["area_cd"])

        lines = [
            f"{area['area_nm']} 상권의 향후 12개월 매출을 예측했습니다.",
            "",
            "예측 결과 (80% 신뢰구간):",
        ]
        for item in forecast.get("forecast", []):
            lines.append(
                f"• {item['quarter']}: {self._format_money(item['predicted_sales'])} "
                f"({self._format_money(item['lower_bound'])}~{self._format_money(item['upper_bound'])}) "
                f"{self._trend_arrow(item['trend'])} {item['trend']}"
            )
        lines.extend([
            "",
            f"⚡ AI 분석: {forecast.get('trend_summary', '추세 정보를 계산할 수 없습니다.')}",
            f"모델 신뢰도는 약 {forecast.get('confidence', 0) * 100:.0f}%입니다.",
        ])
        return "\n".join(lines)

    async def handle_risk_detail(self, message: str, db: AsyncSession) -> str:
        """위험도 상세 질문 처리."""
        area = await self._resolve_area(message, db)
        if not area:
            return "위험도를 확인할 상권명을 찾지 못했습니다. 예: '홍대 상권 폐업 위험 괜찮아?'"

        result = await self._risk.score(area["area_cd"], db)
        lines = [
            f"{area['area_nm']} 상권의 폐업 위험도는 **{result['risk_score']}점({result['risk_level']})**입니다.",
            f"서울 평균 대비: {result.get('compared_to_avg', '-')}",
            "",
            "주요 위험 요인:",
        ]
        for factor in result.get("main_risk_factors", [])[:3]:
            lines.append(
                f"• {factor['factor']}: {factor['value']} "
                f"(기여도 {factor['contribution']:.2f}) - {factor['description']}"
            )
        breakdown = result.get("score_breakdown", {})
        lines.extend([
            "",
            "세부 점수:",
            f"• 매출: {breakdown.get('sales_score', 0)}점",
            f"• 점포: {breakdown.get('store_score', 0)}점",
            f"• 인구: {breakdown.get('population_score', 0)}점",
        ])
        return "\n".join(lines)

    async def handle_policy(
        self, message: str, user_context: dict
    ) -> str:
        """RAG 검색 → LLM으로 사용자 상황에 맞게 정리 (신청 방법·마감일 포함)."""
        policies = await self._rag.search_policies(message, k=5)

        if not policies:
            return (
                "현재 조건에 맞는 지원 정책을 찾지 못했습니다. "
                "업종·지역·창업 여부를 구체적으로 알려주시면 더 정확히 안내해 드릴 수 있어요."
            )

        lines: list[str] = []
        for p in policies:
            bmax     = p.get("budget_max")
            budget   = f"최대 {bmax:,}만원" if bmax else "문의"
            deadline = p.get("apply_end", "상시")
            lines.append(
                f"• [{p['category']}] **{p['program_nm']}**\n"
                f"  - 대상: {p.get('target', '소상공인')}\n"
                f"  - 지원금: {budget}\n"
                f"  - 마감: {deadline}\n"
                f"  - 링크: {p.get('source_url', '')}"
            )
        policy_text = "\n".join(lines)

        if not self._api_key:
            return f"[관련 지원 정책]\n{policy_text}"

        from langchain_core.messages import HumanMessage, SystemMessage

        ctx = (
            f"질문: {message}\n\n"
            f"관련 정책:\n{policy_text}\n"
        )
        if user_context:
            ctx += f"\n사용자 상황: {json.dumps(user_context, ensure_ascii=False)}\n"
        ctx += "\n위 정책을 사용자 상황에 맞게 설명하고, 신청 방법과 마감일을 포함해 안내하세요."

        resp = await self._get_mini().ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=ctx)]
        )
        return resp.content

    async def handle_comparison(self, message: str, db: AsyncSession) -> str:
        """두 상권 데이터 각각 조회 → 비교 테이블 마크다운 + LLM 코멘트."""
        from app.models.database import CommercialArea, SalesData, StoreCount

        areas = await self._extract_two_areas(message)
        if len(areas) < 2:
            return "비교할 두 상권명을 명확히 입력해 주세요. (예: '홍대 vs 신촌 비교')"

        async def _fetch(area_nm: str) -> dict:
            row = (await db.execute(
                select(CommercialArea)
                .where(CommercialArea.area_nm.ilike(f"%{area_nm}%"))
                .limit(1)
            )).scalars().first()
            if not row:
                return {"area_nm": area_nm, "found": False}

            area_cd  = row.area_cd
            latest_q = (await db.execute(
                select(func.max(SalesData.year_quarter))
                .where(SalesData.area_cd == area_cd)
            )).scalar()

            if not latest_q:
                return {"area_nm": row.area_nm, "found": True, "no_data": True}

            sales = (await db.execute(
                select(SalesData)
                .where(SalesData.area_cd == area_cd, SalesData.year_quarter == latest_q)
                .limit(1)
            )).scalars().first()
            store = (await db.execute(
                select(StoreCount)
                .where(StoreCount.area_cd == area_cd, StoreCount.year_quarter == latest_q)
                .limit(1)
            )).scalars().first()

            return {
                "area_nm":       row.area_nm,
                "found":         True,
                "year_quarter":  latest_q,
                "monthly_sales": sales.monthly_sales_avg if sales else None,
                "store_count":   store.store_count       if store else None,
                "close_rate":    store.close_rate        if store else None,
                "open_rate":     store.open_rate         if store else None,
            }

        # 같은 AsyncSession에서 순차 실행 (concurrent 사용 불가)
        d1 = await _fetch(areas[0])
        d2 = await _fetch(areas[1])

        if not d1.get("found"):
            return f"'{areas[0]}' 상권 정보를 찾을 수 없습니다."
        if not d2.get("found"):
            return f"'{areas[1]}' 상권 정보를 찾을 수 없습니다."

        def _v(d: dict, key: str, fmt: str = "") -> str:
            v = d.get(key)
            if v is None:
                return "-"
            if fmt == "money":
                return f"{v:,}원"
            if fmt == "pct":
                return f"{v:.1f}%"
            return str(v)

        table = (
            f"| 항목 | {d1['area_nm']} | {d2['area_nm']} |\n"
            f"|------|---------|----------|\n"
            f"| 기준 분기 | {_v(d1,'year_quarter')} | {_v(d2,'year_quarter')} |\n"
            f"| 월평균 매출 | {_v(d1,'monthly_sales','money')} | {_v(d2,'monthly_sales','money')} |\n"
            f"| 점포 수 | {_v(d1,'store_count')} | {_v(d2,'store_count')} |\n"
            f"| 폐업률 | {_v(d1,'close_rate','pct')} | {_v(d2,'close_rate','pct')} |\n"
            f"| 개업률 | {_v(d1,'open_rate','pct')} | {_v(d2,'open_rate','pct')} |"
        )

        if not self._api_key:
            return table

        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            f"다음은 두 상권 비교 데이터입니다.\n\n{table}\n\n"
            f"원래 질문: {message}\n\n"
            "비교 테이블은 그대로 유지하고 아래에 두 상권의 핵심 차이점과 "
            "창업자에게 더 적합한 상권 추천을 추가하세요."
        )
        resp = await self._get_mini().ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
        )
        return f"{table}\n\n{resp.content}"

    # ── 메인 스트리밍 채팅 ────────────────────────────────────────────────────

    async def chat(
        self,
        message:      str,
        session_id:   str | None,
        db:           AsyncSession,
        user_context: dict = {},
    ) -> AsyncGenerator[str, None]:
        """
        의도 분류 → 핸들러 → gpt-4o 스트리밍 → Redis 저장.

        Yields: 청크 단위 텍스트 (SSE 스트리밍용)
        """
        history = await self._load_history(session_id) if session_id else []

        intent = await self.classify_intent(message)
        logger.info("intent=%s session=%s msg=%.40s", intent, session_id, message)

        # area가 user_context에 있으면 질의에 포함
        area    = user_context.get("area", "")
        query   = f"{area} {message}".strip() if area else message

        try:
            if intent == "data_query":
                context = await self.handle_data_query(query, db)
            elif intent == "report":
                context = await self.handle_report(query, db)
            elif intent == "prediction":
                context = await self.handle_prediction(query, db)
            elif intent == "risk_detail":
                context = await self.handle_risk_detail(query, db)
            elif intent == "policy":
                context = await self.handle_policy(query, user_context)
            elif intent == "comparison":
                context = await self.handle_comparison(query, db)
            else:
                context = ""
        except Exception as exc:
            logger.error("handler error intent=%s: %s", intent, exc)
            context = ""

        # API 키 없으면 안내 메시지 + 컨텍스트 반환
        if not self._api_key:
            body = context or (
                "안녕하세요! 상생나침반 AI 컨설턴트입니다. "
                "궁금하신 상권이나 창업 정보를 물어보세요."
            )
            reply = _DEV_NOTICE + body
            yield reply
            if session_id:
                await self._save_history(session_id, history, message, reply)
            return

        # gpt-4o 스트리밍
        from langchain_core.messages import HumanMessage, SystemMessage

        hist_msgs    = self._history_to_messages(history)
        user_content = (
            f"[수집된 데이터]\n{context}\n\n사용자 질문: {message}"
            if context else message
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *hist_msgs,
            HumanMessage(content=user_content),
        ]

        full_reply = ""
        async for chunk in self._get_llm().astream(messages):
            token = chunk.content
            if token:
                full_reply += token
                yield token

        if session_id:
            await self._save_history(session_id, history, message, full_reply)

    # ── 보조 메서드 ───────────────────────────────────────────────────────────

    async def _resolve_area(self, message: str, db: AsyncSession) -> dict | None:
        from app.models.database import CommercialArea

        area_nm = await self._extract_area(message)
        row = (await db.execute(
            select(CommercialArea)
            .where(CommercialArea.area_nm.ilike(f"%{area_nm}%"))
            .limit(1)
        )).scalars().first()
        if row:
            return {"area_cd": row.area_cd, "area_nm": row.area_nm}

        tokens = [token.strip(" ,.?") for token in message.split() if len(token.strip(" ,.?")) >= 2]
        for token in tokens:
            row = (await db.execute(
                select(CommercialArea)
                .where(CommercialArea.area_nm.ilike(f"%{token}%"))
                .limit(1)
            )).scalars().first()
            if row:
                return {"area_cd": row.area_cd, "area_nm": row.area_nm}
        fallback_areas = {
            "홍대": {"area_cd": "3130210", "area_nm": "홍대입구"},
            "홍대입구": {"area_cd": "3130210", "area_nm": "홍대입구"},
            "종로3가": {"area_cd": "3110016", "area_nm": "종로3가"},
            "종로": {"area_cd": "3110016", "area_nm": "종로3가"},
        }
        for keyword, area in fallback_areas.items():
            if keyword in message:
                return area
        return None

    async def _score_area_with_new_session(self, area_cd: str) -> dict:
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            return await self._risk.score(area_cd, session)

    async def _forecast_area_with_new_session(self, area_cd: str, periods: int = 4) -> dict:
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            try:
                return await self._forecast.predict(area_cd, periods=periods, db=session)
            except Exception as exc:
                logger.warning("forecast fallback for report area=%s: %s", area_cd, exc)
                return self._fallback_forecast_result(area_cd)

    def _format_risk_result(self, result: dict) -> str:
        factors = "\n".join(
            f"- {f['factor']}: {f['value']} ({f['description']})"
            for f in result.get("main_risk_factors", [])[:3]
        )
        return (
            f"위험도 {result.get('risk_score', 0)}점({result.get('risk_level', '-')})\n"
            f"{result.get('compared_to_avg', '')}\n"
            f"{factors}"
        )

    def _format_forecast_result(self, result: dict) -> str:
        lines = [result.get("trend_summary", "예측 요약 없음")]
        for item in result.get("forecast", []):
            lines.append(
                f"- {item['quarter']}: {self._format_money(item['predicted_sales'])} "
                f"({self._format_money(item['lower_bound'])}~{self._format_money(item['upper_bound'])}, {item['trend']})"
            )
        return "\n".join(lines)

    def _fallback_forecast_result(self, area_cd: str) -> dict:
        base = 230_000_000 if area_cd == "3110016" else 260_000_000
        quarters = ["2026Q2", "2026Q3", "2026Q4", "2027Q1"]
        forecast = []
        for idx, quarter in enumerate(quarters):
            predicted = int(base * (1 + 0.025 * idx) * (0.96 if idx == 3 else 1))
            forecast.append({
                "quarter": quarter,
                "date": ["2026-04-01", "2026-07-01", "2026-10-01", "2027-01-01"][idx],
                "predicted_sales": predicted,
                "lower_bound": int(predicted * 0.82),
                "upper_bound": int(predicted * 1.18),
                "trend": "상승" if idx in (1, 2) else "보합",
            })
        return {
            "area_cd": area_cd,
            "forecast": forecast,
            "trend_summary": "데이터가 부족해 규칙 기반 샘플 예측을 표시합니다.",
            "confidence": 0.62,
        }

    def _format_money(self, value: float | int | None) -> str:
        amount = float(value or 0)
        if amount >= 100_000_000:
            return f"{amount / 100_000_000:.1f}억"
        if amount >= 10_000:
            return f"{amount / 10_000:.0f}만"
        return f"{amount:.0f}원"

    def _trend_arrow(self, trend: str) -> str:
        return {"상승": "↗", "하락": "↘", "보합": "→"}.get(trend, "→")

    async def _extract_area(self, message: str) -> str:
        """메시지에서 상권명·자치구 추출."""
        m = re.search(r"([가-힣]{2,10}(?:구|동|로|가|시장|상권|거리))", message)
        if m:
            return m.group(1)

        if not self._api_key:
            return message.split()[0] if message.split() else "종로"

        from langchain_core.messages import HumanMessage
        from langchain_core.output_parsers import StrOutputParser

        resp = await self._get_mini().ainvoke([
            HumanMessage(
                content=(
                    f"다음 문장에서 서울 상권명이나 지역명만 추출하세요. "
                    f"없으면 '알수없음'을 출력하세요.\n\n문장: {message}\n지역명:"
                )
            )
        ])
        return StrOutputParser().invoke(resp).strip() or "종로"

    async def _extract_two_areas(self, message: str) -> list[str]:
        """비교 질문에서 두 상권명 추출."""
        sep = re.search(
            r"([가-힣\w]+)\s+(?:vs|VS|대|와|과|이랑|랑)\s+([가-힣\w]+)", message
        )
        if sep:
            return [sep.group(1), sep.group(2)]

        names = re.findall(r"([가-힣]{2,8}(?:구|동|로|가|시장|상권))", message)
        if len(names) >= 2:
            return names[:2]

        if not self._api_key:
            return []

        from langchain_core.messages import HumanMessage
        from langchain_core.output_parsers import StrOutputParser

        resp = await self._get_mini().ainvoke([
            HumanMessage(
                content=(
                    f"다음 문장에서 비교 대상 두 지역명을 콤마로 구분하여 출력하세요.\n\n"
                    f"문장: {message}\n지역1,지역2:"
                )
            )
        ])
        parts = [p.strip() for p in StrOutputParser().invoke(resp).split(",")]
        return parts if len(parts) >= 2 else []


# ── 하위 호환 alias ───────────────────────────────────────────────────────────
ChatEngine = WinwinChatEngine
