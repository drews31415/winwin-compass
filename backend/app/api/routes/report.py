from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.schemas import ReportResponse

router = APIRouter()


@router.get("", response_model=list[ReportResponse])
async def list_reports(db: AsyncSession = Depends(get_db)):
    # TODO: DB 조회 연동
    return []


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    # TODO: DB 조회 연동
    return ReportResponse(
        id=report_id,
        title="샘플 리포트",
        content="리포트 내용",
        area="종로구",
    )
