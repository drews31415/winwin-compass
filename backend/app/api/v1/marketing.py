import json
import logging
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

MarketingPurpose = Literal["sns", "review", "flyer", "menu", "event", "pivot"]
MarketingTone = Literal["friendly", "premium", "urgent", "calm", "young"]


class MarketingGenerateRequest(BaseModel):
    business_type: str = Field(default="카페", description="업종")
    area: str = Field(default="마포구", description="지역")
    purpose: MarketingPurpose = Field(default="sns", description="생성 목적")
    tone: MarketingTone = Field(default="friendly", description="문체")
    target_customer: str | None = Field(default=None, description="주요 고객")
    risk_factors: list[str] = Field(default_factory=list, description="위험 요인")
    offer: str | None = Field(default=None, description="행사/혜택")
    menu_items: list[str] = Field(default_factory=list, description="대표 메뉴")
    extra_context: str | None = Field(default=None, description="추가 상황")


class MarketingContent(BaseModel):
    title: str
    channel: str
    content: str
    usage_tip: str


class MarketingGenerateResponse(BaseModel):
    contents: list[MarketingContent]
    action_checklist: list[str]
    source: Literal["openai", "sample"]


PURPOSE_LABELS = {
    "sns": "SNS 홍보문",
    "review": "리뷰 답변",
    "flyer": "전단 문구",
    "menu": "메뉴 소개",
    "event": "이벤트 홍보",
    "pivot": "업종전환/리뉴얼 홍보",
}

TONE_LABELS = {
    "friendly": "친근하고 따뜻한",
    "premium": "고급스럽고 신뢰감 있는",
    "urgent": "즉시 방문을 유도하는",
    "calm": "차분하고 설명적인",
    "young": "젊고 경쾌한",
}


def _sample_contents(body: MarketingGenerateRequest) -> MarketingGenerateResponse:
    purpose = PURPOSE_LABELS[body.purpose]
    tone = TONE_LABELS[body.tone]
    area = body.area or "우리 동네"
    business = body.business_type or "매장"
    target = body.target_customer or "동네 고객"
    offer = body.offer or "오늘 방문 고객 혜택"
    menus = ", ".join(body.menu_items[:3]) if body.menu_items else "대표 메뉴"
    risks = ", ".join(body.risk_factors[:3]) if body.risk_factors else "방문 감소"

    if body.purpose == "review":
        content = (
            f"소중한 후기 감사합니다. {area}에서 {business}을 운영하며 더 나은 경험을 드리기 위해 "
            f"항상 메뉴와 서비스를 점검하고 있습니다. 말씀 주신 부분은 바로 확인해 개선하겠습니다. "
            f"다음 방문 때는 더 만족하실 수 있도록 준비하겠습니다."
        )
        channel = "네이버/카카오 리뷰"
    elif body.purpose == "flyer":
        content = (
            f"{area} {business} 방문 이벤트\n"
            f"{menus} 준비했습니다.\n"
            f"{offer}\n"
            f"점심·퇴근길에 편하게 들러주세요."
        )
        channel = "오프라인 전단"
    elif body.purpose == "menu":
        content = (
            f"{menus}는 {target}이 부담 없이 즐길 수 있도록 준비한 {business} 대표 메뉴입니다. "
            f"매장 이용이 줄어드는 시간대에도 편하게 포장·방문하실 수 있게 운영하고 있습니다."
        )
        channel = "메뉴판/상세 설명"
    elif body.purpose == "pivot":
        content = (
            f"{area} {business}이 새롭게 바뀝니다. 최근 {risks} 흐름을 반영해 메뉴와 운영 시간을 조정했습니다. "
            f"기존 고객에게는 익숙함을, 새로운 고객에게는 방문할 이유를 드리겠습니다."
        )
        channel = "리뉴얼 공지"
    else:
        content = (
            f"{area}에서 찾는 {tone} {business}. {target}을 위해 {menus}를 준비했습니다. "
            f"{offer}도 함께 진행 중입니다. 오늘 가까운 곳에서 편하게 들러보세요."
        )
        channel = "인스타그램/블로그"

    return MarketingGenerateResponse(
        source="sample",
        contents=[
            MarketingContent(
                title=purpose,
                channel=channel,
                content=content,
                usage_tip="매장명, 가격, 운영시간을 실제 정보로 바꾼 뒤 게시하세요.",
            ),
            MarketingContent(
                title="짧은 홍보 문구",
                channel="문자/배너",
                content=f"{area} {business} 오늘의 추천: {menus}. {offer}",
                usage_tip="간판, 배너, 문자 발송용으로 짧게 사용할 수 있습니다.",
            ),
        ],
        action_checklist=[
            "방문이 줄어든 시간대에 맞춰 게시 시간을 정하세요.",
            "대표 메뉴 사진 1장과 가격 정보를 함께 넣으세요.",
            "정책 지원금 신청 전후로 리뉴얼 소식을 함께 알리세요.",
        ],
    )


async def _openai_contents(body: MarketingGenerateRequest) -> MarketingGenerateResponse:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    sample = _sample_contents(body)
    prompt = f"""
상생나침반의 소상공인 마케팅 자동화 기능입니다.
아래 상황에 맞는 실행 가능한 한국어 마케팅 문구를 JSON으로만 작성하세요.

업종: {body.business_type}
지역: {body.area}
목적: {PURPOSE_LABELS[body.purpose]}
톤: {TONE_LABELS[body.tone]}
주요 고객: {body.target_customer or "미지정"}
위험 요인: {", ".join(body.risk_factors) or "미지정"}
혜택/행사: {body.offer or "미지정"}
대표 메뉴: {", ".join(body.menu_items) or "미지정"}
추가 상황: {body.extra_context or "없음"}

형식:
{{
  "contents": [
    {{"title": "...", "channel": "...", "content": "...", "usage_tip": "..."}}
  ],
  "action_checklist": ["...", "...", "..."]
}}
"""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        messages=[
            {"role": "system", "content": "과장 광고를 피하고, 소상공인이 바로 사용할 수 있는 현실적인 문구를 작성합니다."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)
    return MarketingGenerateResponse(
        source="openai",
        contents=[MarketingContent(**item) for item in data.get("contents", [])] or sample.contents,
        action_checklist=data.get("action_checklist") or sample.action_checklist,
    )


@router.post("/generate", response_model=MarketingGenerateResponse)
async def generate_marketing(body: MarketingGenerateRequest):
    """위험 진단 이후 바로 실행할 수 있는 마케팅 문구를 생성한다."""
    if not settings.OPENAI_API_KEY:
        return _sample_contents(body)

    try:
        return await _openai_contents(body)
    except Exception as exc:
        logger.warning("marketing generation fallback: %s", exc)
        return _sample_contents(body)
