from pydantic import BaseModel, ConfigDict, Field


# ── 기존 스키마 ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    area: str | None = None


class ChatResponse(BaseModel):
    message: str
    session_id: str | None = None
    sources: list[str] = Field(default_factory=list)


class ReportResponse(BaseModel):
    id: str
    title: str
    content: str
    area: str
    tags: list[str] = Field(default_factory=list)


# ── 상권 스키마 ───────────────────────────────────────────────────────────────

class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area_cd: str
    area_nm: str
    gu_nm: str
    area_type: str
    geom_lat: float | None = None
    geom_lng: float | None = None


class SalesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area_cd: str
    industry_cd: str
    industry_nm: str
    year_quarter: str
    monthly_sales_avg: int | None = None
    daily_sales_avg: int | None = None
    weekday_sales: int | None = None
    weekend_sales: int | None = None
    time_slot_sales: dict | None = None


class StoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area_cd: str
    year_quarter: str
    industry_cd: str
    store_count: int | None = None
    open_rate: float | None = None
    close_rate: float | None = None


class PopulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    area_cd: str
    year_quarter: str
    total_population: int | None = None
    age_10s: int | None = None
    age_20s: int | None = None
    age_30s: int | None = None
    age_40s: int | None = None
    age_50s: int | None = None
    age_60s: int | None = None
    male_ratio: float | None = None
    female_ratio: float | None = None


class AreaDetailOut(BaseModel):
    area: AreaOut
    latest_quarter: str | None = None
    sales: list[SalesOut] = Field(default_factory=list)
    stores: list[StoreOut] = Field(default_factory=list)
    population: PopulationOut | None = None


class RiskOut(BaseModel):
    area_cd: str
    year_quarter: str
    risk_score: float
    breakdown: dict


class CollectOut(BaseModel):
    area_cd: str
    year_quarter: str
    records_saved: int
    message: str


class AreaMapFeature(BaseModel):
    """지도 마커용 상권 집약 데이터."""
    area_cd: str
    area_nm: str
    gu_nm: str
    area_type: str
    lat: float
    lng: float
    monthly_sales_avg: int = 0
    store_count: int = 0
    risk_score: float = 0.5
    main_industry: str = "기타"


# ── v1 API 스키마 ──────────────────────────────────────────────────────────────

class V1ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    user_context: dict = Field(default_factory=dict)


class ChatSimpleResponse(BaseModel):
    answer: str
    intent: str
    sql: str | None = None


class ReportChartsOut(BaseModel):
    sales_trend: list[dict] = Field(default_factory=list)     # [{quarter, avg_sales}]
    time_slots: list[dict] = Field(default_factory=list)      # [{slot, amount}]
    age_distribution: list[dict] = Field(default_factory=list) # [{age_group, count}]


class ReportOut(BaseModel):
    area_nm: str
    risk_score: float
    report_md: str
    charts: ReportChartsOut
    matched_policies: list[dict] = Field(default_factory=list)


class PolicyMatchResponse(BaseModel):
    policies: list[dict] = Field(default_factory=list)
    total: int = 0


class PolicySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class PolicySearchResponse(BaseModel):
    policies: list[dict] = Field(default_factory=list)
