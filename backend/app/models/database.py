import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, Float, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, engine


# ── 믹스인 ──────────────────────────────────────────────────────────────────

class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class TimestampMixin(CreatedAtMixin):
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


# ── 1. 상권 기본 정보 ────────────────────────────────────────────────────────

class CommercialArea(Base, TimestampMixin):
    __tablename__ = "commercial_areas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    area_cd: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    area_nm: Mapped[str] = mapped_column(String(100))
    gu_nm: Mapped[str] = mapped_column(String(50), index=True)
    area_type: Mapped[str] = mapped_column(String(20))  # 골목/전통시장/발달상권/관광특구
    geom_lat: Mapped[Optional[float]] = mapped_column(Float)
    geom_lng: Mapped[Optional[float]] = mapped_column(Float)

    sales: Mapped[list["SalesData"]] = relationship(back_populates="area", cascade="all, delete-orphan")
    stores: Mapped[list["StoreCount"]] = relationship(back_populates="area", cascade="all, delete-orphan")
    populations: Mapped[list["PopulationData"]] = relationship(back_populates="area", cascade="all, delete-orphan")
    workers: Mapped[list["WorkerPopulation"]] = relationship(back_populates="area", cascade="all, delete-orphan")


# ── 2. 추정매출 ──────────────────────────────────────────────────────────────

class SalesData(Base, CreatedAtMixin):
    __tablename__ = "sales_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    area_cd: Mapped[str] = mapped_column(
        String(20), ForeignKey("commercial_areas.area_cd", ondelete="CASCADE"), index=True
    )
    industry_cd: Mapped[str] = mapped_column(String(20), index=True)
    industry_nm: Mapped[str] = mapped_column(String(100))
    year_quarter: Mapped[str] = mapped_column(String(7), index=True)  # 예: 2024Q3
    monthly_sales_avg: Mapped[Optional[int]] = mapped_column(BigInteger)
    daily_sales_avg: Mapped[Optional[int]] = mapped_column(BigInteger)
    weekday_sales: Mapped[Optional[int]] = mapped_column(BigInteger)
    weekend_sales: Mapped[Optional[int]] = mapped_column(BigInteger)
    # {"06": 123000, "09": 456000, ..., "21": 789000}
    time_slot_sales: Mapped[Optional[dict]] = mapped_column(JSONB)

    area: Mapped["CommercialArea"] = relationship(back_populates="sales")


# ── 3. 점포수 ────────────────────────────────────────────────────────────────

class StoreCount(Base, CreatedAtMixin):
    __tablename__ = "store_counts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    area_cd: Mapped[str] = mapped_column(
        String(20), ForeignKey("commercial_areas.area_cd", ondelete="CASCADE"), index=True
    )
    year_quarter: Mapped[str] = mapped_column(String(7), index=True)
    industry_cd: Mapped[str] = mapped_column(String(20))
    store_count: Mapped[Optional[int]] = mapped_column(Integer)
    open_rate: Mapped[Optional[float]] = mapped_column(Float)
    close_rate: Mapped[Optional[float]] = mapped_column(Float)

    area: Mapped["CommercialArea"] = relationship(back_populates="stores")


# ── 4. 생활인구 ──────────────────────────────────────────────────────────────

class PopulationData(Base, CreatedAtMixin):
    __tablename__ = "population_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    area_cd: Mapped[str] = mapped_column(
        String(20), ForeignKey("commercial_areas.area_cd", ondelete="CASCADE"), index=True
    )
    year_quarter: Mapped[str] = mapped_column(String(7), index=True)
    total_population: Mapped[Optional[int]] = mapped_column(Integer)
    age_10s: Mapped[Optional[int]] = mapped_column(Integer)
    age_20s: Mapped[Optional[int]] = mapped_column(Integer)
    age_30s: Mapped[Optional[int]] = mapped_column(Integer)
    age_40s: Mapped[Optional[int]] = mapped_column(Integer)
    age_50s: Mapped[Optional[int]] = mapped_column(Integer)
    age_60s: Mapped[Optional[int]] = mapped_column(Integer)
    male_ratio: Mapped[Optional[float]] = mapped_column(Float)
    female_ratio: Mapped[Optional[float]] = mapped_column(Float)

    area: Mapped["CommercialArea"] = relationship(back_populates="populations")


# ── 5. 직장인구 ──────────────────────────────────────────────────────────────

class WorkerPopulation(Base, CreatedAtMixin):
    __tablename__ = "worker_population"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    area_cd: Mapped[str] = mapped_column(
        String(20), ForeignKey("commercial_areas.area_cd", ondelete="CASCADE"), index=True
    )
    year_quarter: Mapped[str] = mapped_column(String(7), index=True)
    total_workers: Mapped[Optional[int]] = mapped_column(Integer)
    age_20s: Mapped[Optional[int]] = mapped_column(Integer)
    age_30s: Mapped[Optional[int]] = mapped_column(Integer)
    age_40s: Mapped[Optional[int]] = mapped_column(Integer)
    age_50s: Mapped[Optional[int]] = mapped_column(Integer)

    area: Mapped["CommercialArea"] = relationship(back_populates="workers")


# ── 6. 정책/지원사업 ─────────────────────────────────────────────────────────

class PolicyProgram(Base, CreatedAtMixin):
    __tablename__ = "policy_programs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    program_nm: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(20), index=True)  # 융자/보조금/컨설팅/교육
    target: Mapped[Optional[str]] = mapped_column(Text)
    budget_min: Mapped[Optional[int]] = mapped_column(BigInteger)
    budget_max: Mapped[Optional[int]] = mapped_column(BigInteger)
    apply_start: Mapped[Optional[date]] = mapped_column(Date)
    apply_end: Mapped[Optional[date]] = mapped_column(Date)
    source_url: Mapped[Optional[str]] = mapped_column(String(500))


# ── DB 초기화 ────────────────────────────────────────────────────────────────

async def init_db() -> None:
    """pgvector 확장 활성화 + 전체 테이블 생성 (개발/테스트용)."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.run_sync(Base.metadata.create_all)
