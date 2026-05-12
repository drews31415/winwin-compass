from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.get("")
async def list_policies(
    area: str | None = Query(default=None, description="자치구 이름"),
    category: str | None = Query(default=None, description="정책 카테고리"),
    db: AsyncSession = Depends(get_db),
):
    # TODO: 서울시 API 연동
    return {"area": area, "category": category, "items": []}
