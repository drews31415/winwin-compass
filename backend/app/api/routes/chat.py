import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chat_engine import WinwinChatEngine
from app.core.database import get_db
from app.models.schemas import ChatRequest

router  = APIRouter()
_engine = WinwinChatEngine()


@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    채팅 엔드포인트 — SSE 스트리밍 응답.

    이벤트 형식:
      data: {"token": "..."}\n\n   — 텍스트 청크
      data: [DONE]\n\n             — 스트림 종료
    """
    user_context: dict = {}
    if request.area:
        user_context["area"] = request.area

    async def _generate():
        async for token in _engine.chat(
            message=request.message,
            session_id=request.session_id,
            db=db,
            user_context=user_context,
        ):
            yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # nginx 버퍼링 비활성화
        },
    )
