"""
GET  /api/v1/policy/match   — 사용자 프로필 기반 정책 매칭
POST /api/v1/policy/search  — 자유 텍스트 정책 검색
"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.rag_engine import PolicyRAGEngine
from app.core.database import get_db
from app.models.schemas import (
    PolicyMatchResponse, PolicySearchRequest, PolicySearchResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()
_rag   = PolicyRAGEngine()


@router.get("/match", response_model=PolicyMatchResponse)
async def match_policies(
    business_type: str | None = Query(default=None, description="업종 (예: 카페)"),
    area:          str | None = Query(default=None, description="지역 (예: 마포구)"),
    capital:       int | None = Query(default=None, description="자본금 (만원)"),
    age:           int | None = Query(default=None, description="나이"),
    is_new:        bool       = Query(default=True,  description="예비창업자 여부"),
    db: AsyncSession = Depends(get_db),
):
    """사용자 프로필 기반 지원 정책 매칭."""
    user_profile: dict = {
        k: v for k, v in {
            "business_type": business_type,
            "area":          area,
            "capital":       capital,
            "age":           age,
            "is_new":        is_new,
        }.items() if v is not None
    }

    try:
        policies = await _rag.match_for_user(user_profile)
    except Exception as exc:
        logger.error("policy match failed: %s", exc)
        policies = []

    return PolicyMatchResponse(policies=policies, total=len(policies))


@router.post("/search", response_model=PolicySearchResponse)
async def search_policies(
    body: PolicySearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """자유 텍스트로 관련 지원 정책 검색."""
    try:
        policies = await _rag.search_policies(body.query, k=5)
    except Exception as exc:
        logger.error("policy search failed: %s", exc)
        policies = []

    return PolicySearchResponse(policies=policies)
