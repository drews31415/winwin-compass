"""Policy RAG engine with deterministic demo-policy fallbacks."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PolicyProgram

logger = logging.getLogger(__name__)


DEMO_POLICIES: list[dict[str, Any]] = [
    {
        "id": "POLICY_001",
        "program_nm": "서울시 청년 도전 창업자금",
        "category": "융자",
        "target": "만 39세 이하 예비창업자",
        "budget_min": 1000,
        "budget_max": 5000,
        "apply_start": "2026-03-01",
        "apply_end": "2026-11-30",
        "description": "청년 창업자를 위한 저금리 창업자금 대출",
        "source_url": "https://www.sba.seoul.kr",
        "badges": ["청년", "저금리", "예비창업"],
    },
    {
        "id": "POLICY_002",
        "program_nm": "서울시 여성창업 플래티넘 패키지",
        "category": "보조금",
        "target": "여성 예비창업자 또는 창업 3년 이내",
        "budget_min": 500,
        "budget_max": 3000,
        "apply_start": "2026-04-01",
        "apply_end": "2026-09-30",
        "description": "여성 창업자 전용 사업화 자금 및 멘토링",
        "source_url": "https://www.seoulwomanup.or.kr",
        "badges": ["여성", "보조금", "멘토링"],
    },
    {
        "id": "POLICY_003",
        "program_nm": "시니어 재도전 소상공인 패키지",
        "category": "교육",
        "target": "만 50세 이상 예비창업자 및 업종전환 소상공인",
        "budget_min": 0,
        "budget_max": 1200,
        "apply_start": "2026-02-15",
        "apply_end": "2026-12-15",
        "description": "시니어 창업 교육, 상권 진단, 초기 홍보비를 통합 지원",
        "source_url": "https://www.semas.or.kr",
        "badges": ["시니어", "교육", "홍보"],
    },
    {
        "id": "POLICY_004",
        "program_nm": "소상공인 경영안정 특별자금",
        "category": "융자",
        "target": "서울 소재 소상공인 및 예비창업자",
        "budget_min": 1000,
        "budget_max": 7000,
        "apply_start": "2026-01-10",
        "apply_end": "2026-12-31",
        "description": "임차료, 인테리어, 운영비 부담 완화를 위한 정책자금",
        "source_url": "https://www.sbiz.or.kr",
        "badges": ["1인 창업자", "경영안정", "저금리"],
    },
    {
        "id": "POLICY_005",
        "program_nm": "서울신용보증재단 창업보증",
        "category": "보증",
        "target": "담보력이 부족한 서울시 창업자",
        "budget_min": 0,
        "budget_max": 10000,
        "apply_start": "2026-01-01",
        "apply_end": "2026-12-31",
        "description": "창업 초기 대출 접근성을 높이기 위한 신용보증 지원",
        "source_url": "https://www.seoulshinbo.co.kr",
        "badges": ["1인 창업자", "보증", "고위험 우선"],
    },
]


class PolicyRAGEngine:
    """Search policy documents with pgvector when available, otherwise use demo policies."""

    def __init__(self) -> None:
        from app.core.config import settings

        self._api_key = settings.OPENAI_API_KEY
        self._dev_mode = not bool(self._api_key)

        raw = settings.DATABASE_URL
        if "+asyncpg" in raw:
            self._pg_url = raw.replace("+asyncpg", "+psycopg")
        elif raw.startswith("postgresql://"):
            self._pg_url = raw.replace("postgresql://", "postgresql+psycopg://", 1)
        else:
            self._pg_url = raw

        self._embeddings: Any = None
        self._vectorstore: Any = None
        self._llm: Any = None

    def _get_embeddings(self):
        if self._embeddings is None:
            from langchain_openai import OpenAIEmbeddings

            self._embeddings = OpenAIEmbeddings(
                model="text-embedding-3-small",
                api_key=self._api_key,
            )
        return self._embeddings

    def _get_vectorstore(self):
        if self._vectorstore is None:
            from langchain_postgres import PGVector

            self._vectorstore = PGVector(
                embeddings=self._get_embeddings(),
                collection_name="policies",
                connection=self._pg_url,
                use_jsonb=True,
            )
        return self._vectorstore

    def _get_llm(self):
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.2,
                api_key=self._api_key,
            )
        return self._llm

    @staticmethod
    def _to_document(policy: dict[str, Any]):
        from langchain_core.documents import Document

        budget = (
            f"{policy.get('budget_min', 0):,}~{policy['budget_max']:,}만원"
            if policy.get("budget_max")
            else "문의"
        )
        apply_period = f"{policy.get('apply_start', '상시')}~{policy.get('apply_end') or '상시'}"
        content = (
            f"{policy['program_nm']}. 대상: {policy.get('target', '')}. "
            f"지원내용: {policy.get('description', '')}. 예산: {budget}. "
            f"신청기간: {apply_period}"
        )
        return Document(
            page_content=content,
            metadata={
                "id": str(policy.get("id", "")),
                "category": policy.get("category", ""),
                "apply_end": str(policy.get("apply_end") or ""),
                "source_url": policy.get("source_url", ""),
                "program_nm": policy["program_nm"],
                "budget_max": policy.get("budget_max"),
                "target": policy.get("target", ""),
                "description": policy.get("description", ""),
            },
        )

    async def add_policy_documents(self, policies: list[dict[str, Any]]) -> int:
        """Index policies into pgvector."""
        if self._dev_mode:
            logger.warning("add_policy_documents skipped: OPENAI_API_KEY is not set")
            return 0

        docs = [self._to_document(policy) for policy in policies]
        ids = await self._get_vectorstore().aadd_documents(docs)
        logger.info("Indexed %d policy documents", len(ids))
        return len(ids)

    async def search_policies(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Search relevant policies, filtering expired programs."""
        if self._dev_mode:
            return self._dev_search(query)[:k]

        try:
            raw = await self._get_vectorstore().asimilarity_search_with_relevance_scores(query, k=k)
            today = date.today().isoformat()
            results: list[dict[str, Any]] = []
            for doc, score in raw:
                apply_end = doc.metadata.get("apply_end", "")
                if score < 0.7 or (apply_end and apply_end < today):
                    continue
                results.append(
                    {
                        "program_nm": doc.metadata.get("program_nm", ""),
                        "category": doc.metadata.get("category", ""),
                        "target": doc.metadata.get("target", ""),
                        "budget_max": doc.metadata.get("budget_max"),
                        "apply_end": apply_end or "상시",
                        "source_url": doc.metadata.get("source_url", ""),
                        "description": doc.metadata.get("description", ""),
                        "content": doc.page_content,
                        "score": round(float(score), 4),
                        "badges": [],
                    }
                )
            return self._rank_policies(results, {})
        except Exception as exc:
            logger.warning("Vector policy search failed, using demo fallback: %s", exc)
            return self._dev_search(query)[:k]

    async def match_for_user(self, user_profile: dict[str, Any]) -> list[dict[str, Any]]:
        """Match policies for a user profile and add a short reason."""
        query = self._build_profile_query(user_profile)
        policies = await self.search_policies(query, k=5)
        if not policies:
            return policies

        if self._dev_mode:
            for policy in policies:
                policy["match_reason"] = self._fallback_match_reason(policy, user_profile)
            return self._rank_policies(policies, user_profile)

        for policy in policies:
            try:
                policy["match_reason"] = await self._explain_match(policy, user_profile)
            except Exception:
                policy["match_reason"] = self._fallback_match_reason(policy, user_profile)
        return self._rank_policies(policies, user_profile)

    def _build_profile_query(self, profile: dict[str, Any]) -> str:
        parts: list[str] = []
        if business_type := profile.get("business_type"):
            parts.append(f"{business_type} 창업")
        if area := profile.get("area"):
            parts.append(f"{area} 소상공인")
        if profile.get("is_new", True):
            parts.append("예비창업 초기창업")
        if capital := profile.get("capital"):
            parts.append(f"자본금 {capital}만원")
        if (age := profile.get("age")) and age < 40:
            parts.append("청년창업")
        if (age := profile.get("age")) and age >= 50:
            parts.append("시니어 재도전")
        if user_types := profile.get("user_types"):
            parts.extend(user_types)
        if (risk_score := profile.get("risk_score")) and risk_score >= 70:
            parts.append("긴급 경영안정 저금리 대출 업종전환 지원")
        return " ".join(parts) or "소상공인 창업 지원 정책"

    async def _explain_match(self, policy: dict[str, Any], profile: dict[str, Any]) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = (
            "다음 사용자에게 정책이 적합한 이유를 2문장으로 설명하세요.\n"
            f"사용자: {profile}\n정책: {policy}"
        )
        response = await self._get_llm().ainvoke(
            [
                SystemMessage(content="당신은 서울시 소상공인 정책 상담가입니다."),
                HumanMessage(content=prompt),
            ]
        )
        return response.content.strip()

    @staticmethod
    def _fallback_match_reason(policy: dict[str, Any], profile: dict[str, Any]) -> str:
        age = profile.get("age")
        business_type = profile.get("business_type") or "창업"
        area = profile.get("area") or "서울"
        risk_score = profile.get("risk_score")
        user_types = ", ".join(profile.get("user_types") or [])
        if risk_score and risk_score >= 70 and policy.get("category") in {"융자", "보증"}:
            return f"폐업 위험 {risk_score}점으로 긴급 자금 대응이 우선입니다. {area} {business_type} 조건과 {user_types or '예비창업자'} 상황을 반영해 경영안정 자금으로 검토할 수 있습니다."
        if age and age < 40 and "청년" in policy["program_nm"]:
            return f"만 39세 이하 조건에 맞고, {business_type} 초기 자금으로 활용하기 좋습니다."
        if age and age >= 50 and "시니어" in policy["program_nm"]:
            return "시니어 창업 교육과 초기 운영 지원을 함께 받을 수 있어 진입 부담을 낮춥니다."
        if "여성" in policy["program_nm"]:
            return "여성 예비창업자에게 사업화 자금과 멘토링을 함께 지원하는 정책입니다."
        return "예비창업자의 초기 자금 부담을 줄이는 데 적합한 지원 정책입니다."

    @staticmethod
    def _rank_policies(policies: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
        user_types = set(profile.get("user_types") or [])
        risk_score = profile.get("risk_score") or 0

        def score(policy: dict[str, Any]) -> float:
            value = float(policy.get("score") or policy.get("match_score") or 0.7)
            badges = set(policy.get("badges") or [])
            value += 0.08 * len(user_types & badges)
            if risk_score >= 70 and (policy.get("category") in {"융자", "보증"} or "경영안정" in badges):
                value += 0.2
                policy["priority"] = "폐업 위험 고위험 우선 추천"
                policy["badges"] = list(badges | {"고위험 우선"})
            policy["match_score"] = min(0.98, round(value, 3))
            return value

        return sorted(policies, key=score, reverse=True)

    async def seed_sample_policies(self) -> int:
        """Seed demo policy documents into pgvector when OpenAI is configured."""
        if self._dev_mode:
            logger.warning("seed_sample_policies skipped: OPENAI_API_KEY is not set")
            return 0

        try:
            existing = await self.search_policies("서울시 창업 지원", k=1)
            if existing:
                return 0
        except Exception:
            pass
        return await self.add_policy_documents(DEMO_POLICIES)

    async def format_as_context(self, query: str, session: AsyncSession | None = None) -> str:
        """Format matching policies as LLM context."""
        if self._dev_mode and session is not None:
            return await self._orm_context(query, session)

        policies = await self.search_policies(query, k=3)
        if not policies:
            return "현재 등록된 관련 정책이 없습니다."

        lines = ["[관련 지원 정책]"]
        for policy in policies:
            budget = f" (최대 {policy['budget_max']:,}만원)" if policy.get("budget_max") else ""
            lines.append(f"- [{policy['category']}] {policy['program_nm']}{budget}")
            if policy.get("target"):
                lines.append(f"  대상: {policy['target']}")
            if policy.get("apply_end"):
                lines.append(f"  신청 마감: {policy['apply_end']}")
        return "\n".join(lines)

    async def _orm_context(self, query: str, session: AsyncSession) -> str:
        keywords = [word for word in query.split() if len(word) >= 2][:5]
        if keywords:
            conds = [
                or_(
                    PolicyProgram.program_nm.ilike(f"%{keyword}%"),
                    PolicyProgram.target.ilike(f"%{keyword}%"),
                    PolicyProgram.category.ilike(f"%{keyword}%"),
                )
                for keyword in keywords
            ]
            rows = (
                await session.execute(select(PolicyProgram).where(or_(*conds)).limit(3))
            ).scalars().all()
        else:
            rows = (await session.execute(select(PolicyProgram).limit(3))).scalars().all()

        if not rows:
            policies = self._dev_search(query)[:3]
            lines = ["[관련 지원 정책]"]
            for policy in policies:
                lines.append(f"- [{policy['category']}] {policy['program_nm']}")
            return "\n".join(lines)

        lines = ["[관련 지원 정책]"]
        for row in rows:
            budget = f" (최대 {row.budget_max:,}만원)" if row.budget_max else ""
            lines.append(f"- [{row.category}] {row.program_nm}{budget}")
            if row.target:
                lines.append(f"  대상: {row.target}")
        return "\n".join(lines)

    @staticmethod
    def _dev_search(query: str) -> list[dict[str, Any]]:
        keywords = [word.lower() for word in query.split() if len(word) >= 2]
        results: list[dict[str, Any]] = []
        today = date.today().isoformat()

        for policy in DEMO_POLICIES:
            if policy.get("apply_end") and policy["apply_end"] < today:
                continue
            haystack = " ".join(
                [
                    policy["program_nm"],
                    policy.get("category", ""),
                    policy.get("target", ""),
                    policy.get("description", ""),
                ]
            ).lower()
            if not keywords or any(keyword in haystack for keyword in keywords):
                results.append(
                    {
                        "program_nm": policy["program_nm"],
                        "category": policy["category"],
                        "target": policy.get("target", ""),
                        "budget_max": policy.get("budget_max"),
                        "apply_end": str(policy.get("apply_end") or "상시"),
                        "source_url": policy.get("source_url", ""),
                        "description": policy.get("description", ""),
                        "badges": policy.get("badges", []),
                        "content": (
                            f"{policy['program_nm']}. 대상: {policy.get('target', '')}. "
                            f"지원내용: {policy.get('description', '')}."
                        ),
                        "score": 0.0,
                    }
                )

        return results or [
            {
                "program_nm": policy["program_nm"],
                "category": policy["category"],
                "target": policy.get("target", ""),
                "budget_max": policy.get("budget_max"),
                "apply_end": str(policy.get("apply_end") or "상시"),
                "source_url": policy.get("source_url", ""),
                "description": policy.get("description", ""),
                "badges": policy.get("badges", []),
                "content": policy.get("description", ""),
                "score": 0.0,
            }
            for policy in DEMO_POLICIES[:3]
        ]


PolicyRAG = PolicyRAGEngine
