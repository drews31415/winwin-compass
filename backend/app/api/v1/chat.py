"""
POST /api/v1/chat         — SSE 스트리밍 채팅
POST /api/v1/chat/simple  — 단일 JSON 응답 (테스트용)
"""
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat_engine import GolmokChatEngine, _DEV_NOTICE
from app.core.database import get_db
from app.models.schemas import ChatSimpleResponse, V1ChatRequest

logger = logging.getLogger(__name__)
router  = APIRouter()
_engine = GolmokChatEngine()


@router.post("")
async def chat_stream(
    request: V1ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    SSE 스트리밍 채팅.

    이벤트 형식:
      data: {"chunk": "..."}\n\n   — 텍스트 청크
      data: [DONE]\n\n             — 스트림 종료
    """
    async def _generate():
        try:
            async for token in _engine.chat(
                message=request.message,
                session_id=request.session_id,
                db=db,
                user_context=request.user_context,
            ):
                yield f"data: {json.dumps({'chunk': token}, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.error("chat stream error: %s", exc)
            err = json.dumps({"chunk": "죄송합니다. 처리 중 오류가 발생했습니다."}, ensure_ascii=False)
            yield f"data: {err}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/simple", response_model=ChatSimpleResponse)
async def chat_simple(
    request: V1ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """스트리밍 없는 단일 JSON 응답 (테스트·디버그용)."""
    intent = await _engine.classify_intent(request.message)

    # 스트리밍 응답 전체 수집
    chunks: list[str] = []
    try:
        async for token in _engine.chat(
            message=request.message,
            session_id=request.session_id,
            db=db,
            user_context=request.user_context,
        ):
            chunks.append(token)
        answer = "".join(chunks)
    except Exception as exc:
        logger.warning("chat simple fallback: %s", exc)
        answer = (
            "현재 실시간 데이터베이스 연결이 없어 샘플 분석을 제공합니다. "
            "마포구 카페 창업은 유동인구와 경쟁 강도를 함께 봐야 하며, "
            "초기에는 임대료 부담이 낮고 테이크아웃 수요가 있는 상권을 우선 검토하는 것이 좋습니다."
        )

    # data_query 의도일 때만 SQL 추출
    sql: str | None = None
    if intent == "data_query":
        if _engine._api_key:
            try:
                sql = await _engine._sql.generate_sql(request.message)
            except Exception as exc:
                logger.debug("sql extraction failed: %s", exc)
        else:
            from app.ai.text_to_sql import _DEV_SQL
            sql = _DEV_SQL

    # dev 모드일 때 answer 앞에 안내 메시지 삽입 (이미 chat()에서 주입되지만 명시적 보장)
    if not _engine._api_key and not answer.startswith(_DEV_NOTICE[:10]):
        answer = _DEV_NOTICE + answer

    return ChatSimpleResponse(answer=answer, intent=intent, sql=sql)
