"""
RAG 엔진 — pgvector + LangChain으로 정책 문서 벡터 검색.

검색 전략:
  OPENAI_API_KEY 있음: PGVector 유사도 검색 (score > 0.7, 마감일 필터)
  OPENAI_API_KEY 없음: 인메모리 샘플 키워드 검색 (dev 모드)

langchain-postgres PGVector는 langchain_pg_collection / langchain_pg_embedding
테이블을 자동으로 생성 (ORM 테이블과 별개).
"""
import logging
from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PolicyProgram

logger = logging.getLogger(__name__)

# ── 매칭 설명 프롬프트 ────────────────────────────────────────────────────────

_MATCH_PROMPT = """사용자 프로필:
- 업종: {business_type}
- 지역: {area}
- 자본금: {capital}만원
- 나이: {age}세
- 창업 유형: {startup_type}

지원 정책:
{policy_info}

이 사용자에게 위 정책이 적합한 이유를 2~3문장으로 간결하게 설명하세요."""

# ── 샘플 정책 (dev 모드 + seed 용) ───────────────────────────────────────────

_SAMPLE_POLICIES: list[dict] = [
    {
        "id": "POLICY_001",
        "program_nm": "소상공인 정책자금",
        "description": "소상공인의 사업 운영 및 성장을 위한 정책 융자 지원",
        "category": "융자",
        "target": "업력 3년 이상 소상공인",
        "budget_min": 1000,
        "budget_max": 7000,
        "apply_start": "2024-01-01",
        "apply_end": "2024-12-31",
        "source_url": "https://www.sbiz.or.kr",
    },
    {
        "id": "POLICY_002",
        "program_nm": "서울시 청년창업 지원사업",
        "description": "서울시 청년의 혁신적 창업 아이디어 실현을 위한 초기 창업 자금 지원",
        "category": "보조금",
        "target": "만 19세~39세 서울 거주 예비창업자 또는 창업 3년 이내",
        "budget_min": 500,
        "budget_max": 3000,
        "apply_start": "2024-03-01",
        "apply_end": "2024-09-30",
        "source_url": "https://www.sba.seoul.kr",
    },
    {
        "id": "POLICY_003",
        "program_nm": "서울신용보증재단 창업보증",
        "description": "담보 여력이 부족한 소상공인·자영업자의 금융 접근성 제고를 위한 보증 지원",
        "category": "보증",
        "target": "서울 소재 창업 예정자 및 사업자",
        "budget_min": None,
        "budget_max": 10000,
        "apply_start": "2024-01-01",
        "apply_end": None,
        "source_url": "https://www.seoulshinbo.co.kr",
    },
    {
        "id": "POLICY_004",
        "program_nm": "소상공인시장진흥공단 무료 경영컨설팅",
        "description": "경영 애로 소상공인 대상 전문 컨설턴트 1:1 무료 경영 진단 및 개선 지원",
        "category": "컨설팅",
        "target": "매출 감소, 경영 위기 소상공인 우선",
        "budget_min": None,
        "budget_max": None,
        "apply_start": "2024-01-01",
        "apply_end": "2024-12-31",
        "source_url": "https://www.semas.or.kr",
    },
    {
        "id": "POLICY_005",
        "program_nm": "서울시 골목상권 활성화 지원",
        "description": "골목상권 내 소상공인 시설 개선 및 환경 조성 비용 보조. 간판·인테리어·설비 지원",
        "category": "보조금",
        "target": "서울시 지정 골목상권 내 소상공인",
        "budget_min": 200,
        "budget_max": 2000,
        "apply_start": "2024-04-01",
        "apply_end": "2024-10-31",
        "source_url": "https://golmok.seoul.go.kr",
    },
]


# ── PolicyRAGEngine ───────────────────────────────────────────────────────────

class PolicyRAGEngine:
    """pgvector + LangChain 기반 정책 문서 RAG 엔진."""

    def __init__(self) -> None:
        from app.core.config import settings

        self._api_key = settings.OPENAI_API_KEY
        self._dev_mode = not bool(self._api_key)

        # langchain-postgres PGVector는 psycopg3 연결 문자열 필요
        raw = settings.DATABASE_URL
        if "+asyncpg" in raw:
            self._pg_url = raw.replace("+asyncpg", "+psycopg")
        elif raw.startswith("postgresql://"):
            self._pg_url = raw.replace("postgresql://", "postgresql+psycopg://", 1)
        else:
            self._pg_url = raw

        self._embeddings: Any  = None
        self._vectorstore: Any = None
        self._llm: Any         = None

    # ── 지연 초기화 ───────────────────────────────────────────────────────────

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

    # ── Document 변환 ─────────────────────────────────────────────────────────

    @staticmethod
    def _to_document(policy: dict):
        from langchain_core.documents import Document

        budget_str = (
            f"{policy.get('budget_min', 0)}~{policy['budget_max']}만원"
            if policy.get("budget_max")
            else "문의"
        )
        apply_str = (
            f"{policy.get('apply_start', '상시')}~{policy.get('apply_end') or '상시'}"
        )
        content = (
            f"{policy['program_nm']}. "
            f"대상: {policy.get('target', '소상공인')}. "
            f"지원내용: {policy.get('description', '')}. "
            f"예산: {budget_str}. "
            f"신청기간: {apply_str}"
        )
        metadata = {
            "id":         str(policy.get("id", "")),
            "category":   policy.get("category", ""),
            "apply_end":  str(policy.get("apply_end") or ""),
            "source_url": policy.get("source_url", ""),
            "program_nm": policy["program_nm"],
            "budget_max": policy.get("budget_max"),
            "target":     policy.get("target", ""),
        }
        return Document(page_content=content, metadata=metadata)

    # ── 1. 정책 적재 ──────────────────────────────────────────────────────────

    async def add_policy_documents(self, policies: list[dict]) -> int:
        """
        정책 데이터 → Document 변환 → PGVector 적재.

        Returns: 적재된 Document 수
        """
        if self._dev_mode:
            logger.warning("add_policy_documents: dev mode — skipped (OPENAI_API_KEY 미설정)")
            return 0

        try:
            docs = [self._to_document(p) for p in policies]
            vs   = self._get_vectorstore()
            ids  = await vs.aadd_documents(docs)
            logger.info("add_policy_documents: %d docs indexed", len(ids))
            return len(ids)
        except Exception as exc:
            logger.error("add_policy_documents failed: %s", exc)
            raise

    # ── 2. 유사도 검색 ────────────────────────────────────────────────────────

    async def search_policies(
        self, query: str, k: int = 5
    ) -> list[dict[str, Any]]:
        """
        PGVector 유사도 검색.

        필터:
          - relevance score > 0.7  (낮으면 관련성 부족)
          - apply_end > 오늘 또는 없음 (상시 접수)

        dev 모드: 인메모리 샘플 키워드 검색으로 폴백.
        """
        if self._dev_mode:
            return self._dev_search(query)

        try:
            vs    = self._get_vectorstore()
            raw   = await vs.asimilarity_search_with_relevance_scores(query, k=k)
            today = date.today().isoformat()

            results: list[dict] = []
            for doc, score in raw:
                if score < 0.7:
                    continue
                apply_end = doc.metadata.get("apply_end", "")
                if apply_end and apply_end < today:
                    continue

                results.append({
                    "program_nm": doc.metadata.get("program_nm", ""),
                    "category":   doc.metadata.get("category", ""),
                    "target":     doc.metadata.get("target", ""),
                    "budget_max": doc.metadata.get("budget_max"),
                    "apply_end":  apply_end or "상시",
                    "source_url": doc.metadata.get("source_url", ""),
                    "content":    doc.page_content,
                    "score":      round(score, 4),
                })

            logger.info("search_policies: '%s' → %d results", query[:40], len(results))
            return results

        except Exception as exc:
            logger.error("search_policies failed (%s) — dev fallback", exc)
            return self._dev_search(query)

    # ── 3. 사용자 프로필 기반 매칭 ────────────────────────────────────────────

    async def match_for_user(
        self, user_profile: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        사용자 프로필 → 검색 쿼리 자동 생성 → 유사도 검색 → LLM 매칭 이유 추가.

        Args:
            user_profile: {
                "business_type": str,   # 예: "카페"
                "area":          str,   # 예: "마포구"
                "capital":       int,   # 자본금 (만원)
                "age":           int,
                "is_new":        bool,  # True=예비창업자
            }
        Returns:
            search_policies 결과에 "match_reason" 필드 추가
        """
        query    = self._build_profile_query(user_profile)
        policies = await self.search_policies(query, k=5)

        if not policies or self._dev_mode:
            return policies

        startup_type = "예비창업자" if user_profile.get("is_new") else "기창업자"
        for policy in policies:
            try:
                policy["match_reason"] = await self._explain_match(
                    policy, user_profile, startup_type
                )
            except Exception as exc:
                logger.warning("match_reason generation failed: %s", exc)
                policy["match_reason"] = ""

        return policies

    def _build_profile_query(self, profile: dict) -> str:
        parts: list[str] = []
        if bt := profile.get("business_type"):
            parts.append(f"{bt} 창업 지원")
        if area := profile.get("area"):
            parts.append(f"{area} 지역 소상공인")
        if profile.get("is_new"):
            parts.append("예비창업자 신규창업 초기창업")
        if capital := profile.get("capital"):
            parts.append(f"자본금 {capital}만원 창업자금")
        if (age := profile.get("age")) and age < 40:
            parts.append("청년창업")
        return " ".join(parts) or "소상공인 창업 지원 정책"

    async def _explain_match(
        self, policy: dict, profile: dict, startup_type: str
    ) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        prompt = _MATCH_PROMPT.format(
            business_type=profile.get("business_type", "미지정"),
            area=profile.get("area", "미지정"),
            capital=profile.get("capital", "미지정"),
            age=profile.get("age", "미지정"),
            startup_type=startup_type,
            policy_info=policy.get("content", policy.get("program_nm", "")),
        )
        response = await self._get_llm().ainvoke([
            SystemMessage(content="당신은 소상공인 정책 전문가입니다."),
            HumanMessage(content=prompt),
        ])
        return response.content.strip()

    # ── 4. 샘플 데이터 적재 ───────────────────────────────────────────────────

    async def seed_sample_policies(self) -> int:
        """
        개발용 샘플 정책 5건을 벡터 DB에 적재.
        이미 적재된 경우 스킵.
        """
        if self._dev_mode:
            logger.warning("seed_sample_policies: dev mode — skipped (OPENAI_API_KEY 미설정)")
            return 0

        try:
            existing = await self.search_policies("소상공인 지원", k=1)
            if existing:
                logger.info("seed_sample_policies: already seeded — skipped")
                return 0
        except Exception:
            pass

        count = await self.add_policy_documents(_SAMPLE_POLICIES)
        logger.info("seed_sample_policies: %d policies seeded", count)
        return count

    # ── chat_engine 호환: format_as_context ───────────────────────────────────

    async def format_as_context(
        self,
        query: str,
        session: AsyncSession | None = None,
    ) -> str:
        """
        검색 결과를 LLM 컨텍스트용 문자열로 변환.

        session 파라미터: 이전 PolicyRAG 호환용 (미사용, PGVector 직접 검색).
        OPENAI_API_KEY 없으면 policy_programs ORM 테이블 ILIKE 검색으로 폴백.
        """
        if self._dev_mode and session is not None:
            return await self._orm_context(query, session)

        policies = await self.search_policies(query, k=3)
        if not policies:
            return "현재 등록된 관련 정책이 없습니다."

        lines = ["[관련 지원 정책]"]
        for p in policies:
            bmax = p.get("budget_max")
            budget = f" (최대 {bmax:,}만원)" if bmax else ""
            lines.append(f"• [{p['category']}] {p['program_nm']}{budget}")
            if target := p.get("target"):
                lines.append(f"  대상: {target}")
            if apply_end := p.get("apply_end"):
                lines.append(f"  신청 마감: {apply_end}")
        return "\n".join(lines)

    async def _orm_context(self, query: str, session: AsyncSession) -> str:
        """dev 모드 폴백 — policy_programs ORM ILIKE 검색."""
        keywords = [w for w in query.split() if len(w) >= 2][:5]
        if not keywords:
            rows = (await session.execute(select(PolicyProgram).limit(3))).scalars().all()
        else:
            conds = [
                or_(
                    PolicyProgram.program_nm.ilike(f"%{kw}%"),
                    PolicyProgram.target.ilike(f"%{kw}%"),
                    PolicyProgram.category.ilike(f"%{kw}%"),
                )
                for kw in keywords
            ]
            rows = (
                await session.execute(
                    select(PolicyProgram).where(or_(*conds)).limit(3)
                )
            ).scalars().all()

        if not rows:
            # ORM에도 없으면 인메모리 샘플 사용
            samples = self._dev_search(query)
            if not samples:
                return "현재 등록된 관련 정책이 없습니다."
            lines = ["[관련 지원 정책 (샘플)]"]
            for p in samples[:3]:
                lines.append(f"• [{p['category']}] {p['program_nm']}")
                if p.get("target"):
                    lines.append(f"  대상: {p['target']}")
            return "\n".join(lines)

        lines = ["[관련 지원 정책]"]
        for p in rows:
            bmax = p.budget_max
            budget = f" (최대 {bmax:,}원)" if bmax else ""
            lines.append(f"• [{p.category}] {p.program_nm}{budget}")
            if p.target:
                lines.append(f"  대상: {p.target}")
        return "\n".join(lines)

    # ── dev 모드 인메모리 키워드 검색 ─────────────────────────────────────────

    @staticmethod
    def _dev_search(query: str) -> list[dict[str, Any]]:
        """샘플 정책을 키워드로 필터링 (API 키 불필요)."""
        keywords = [w.lower() for w in query.split() if len(w) >= 2]
        results: list[dict] = []

        for p in _SAMPLE_POLICIES:
            haystack = " ".join([
                p["program_nm"],
                p.get("target", ""),
                p.get("description", ""),
                p["category"],
            ]).lower()
            if not keywords or any(kw in haystack for kw in keywords):
                bmax = p.get("budget_max")
                results.append({
                    "program_nm": p["program_nm"],
                    "category":   p["category"],
                    "target":     p.get("target", ""),
                    "budget_max": bmax,
                    "apply_end":  str(p.get("apply_end") or "상시"),
                    "source_url": p.get("source_url", ""),
                    "content": (
                        f"{p['program_nm']}. 대상: {p.get('target','')}. "
                        f"지원내용: {p.get('description','')}."
                    ),
                    "score": 0.0,
                })

        return results[:5]


# ── 하위 호환 alias ───────────────────────────────────────────────────────────
PolicyRAG = PolicyRAGEngine
