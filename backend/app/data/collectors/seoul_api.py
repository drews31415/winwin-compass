import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.data.collectors.base import BaseCollector, parse_seoul_response
from app.models.database import (
    CommercialArea,
    PopulationData,
    SalesData,
    StoreCount,
    WorkerPopulation,
)

logger = logging.getLogger(__name__)

_BASE_URL = "http://openapi.seoul.go.kr:8088"


# ── 변환 헬퍼 ────────────────────────────────────────────────────────────────

def _int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val not in (None, "", " ") else default
    except (ValueError, TypeError):
        return default


def _float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val not in (None, "", " ") else default
    except (ValueError, TypeError):
        return default


def _quarter(row: dict) -> str:
    """STDR_YY_CD + STDR_QU_CD → "2024Q3" 포맷."""
    return f"{row.get('STDR_YY_CD', '2024')}Q{row.get('STDR_QU_CD', '3')}"


# ── 개발용 더미 데이터 ────────────────────────────────────────────────────────

_DUMMY_AREAS = [
    {
        "TRDAR_CD": "DEV001", "TRDAR_CD_NM": "테스트골목상권",
        "TRDAR_SE_CD_NM": "골목상권",
        "X_COORDINATE": "126.9784", "Y_COORDINATE": "37.5665",
        "SIGNGU_CD_NM": "중구",
    },
    {
        "TRDAR_CD": "DEV002", "TRDAR_CD_NM": "테스트전통시장",
        "TRDAR_SE_CD_NM": "전통시장",
        "X_COORDINATE": "126.9230", "Y_COORDINATE": "37.5547",
        "SIGNGU_CD_NM": "종로구",
    },
]

_DUMMY_SALES_ROW = {
    "STDR_YY_CD": "2024", "STDR_QU_CD": "3",
    "TRDAR_CD": "DEV001", "TRDAR_CD_NM": "테스트골목상권",
    "SVC_INDUTY_CD": "CS100001", "SVC_INDUTY_CD_NM": "한식음식점",
    "MDWK_SELNG_AMT": "15000000", "WKND_SELNG_AMT": "8000000",
    "TMZ_CD_01": "500000",  "TMZ_CD_02": "2000000",
    "TMZ_CD_03": "5000000", "TMZ_CD_04": "3000000",
    "TMZ_CD_05": "4000000", "TMZ_CD_06": "500000",
}

_DUMMY_STORE_ROW = {
    "STDR_YY_CD": "2024", "STDR_QU_CD": "3",
    "TRDAR_CD": "DEV001",
    "SVC_INDUTY_CD": "CS100001",
    "STOR_CO": "42", "OPR_RATE_RT": "3.2", "CLR_RATE_RT": "2.1",
}

_DUMMY_POP_ROW = {
    "STDR_YY_CD": "2024", "STDR_QU_CD": "3",
    "TRDAR_CD": "DEV001",
    "TOT_FLPOP_CO": "12000",
    "AGRDE_10_FLPOP_CO": "800",  "AGRDE_20_FLPOP_CO": "2800",
    "AGRDE_30_FLPOP_CO": "3100", "AGRDE_40_FLPOP_CO": "2500",
    "AGRDE_50_FLPOP_CO": "1900", "AGRDE_60_ABOVE_FLPOP_CO": "900",
    "ML_FLPOP_CO": "5800", "FML_FLPOP_CO": "6200",
}

_DUMMY_WORKER_ROW = {
    "STDR_YY_CD": "2024", "STDR_QU_CD": "3",
    "TRDAR_CD": "DEV001",
    "TOT_WRC_POPLTN_CO": "3500",
    "AGRDE_20_WRC_POPLTN_CO": "700",  "AGRDE_30_WRC_POPLTN_CO": "1100",
    "AGRDE_40_WRC_POPLTN_CO": "950",  "AGRDE_50_WRC_POPLTN_CO": "600",
}


# ── SeoulOpenAPI ─────────────────────────────────────────────────────────────

class SeoulOpenAPI(BaseCollector):
    """
    서울 열린데이터광장 상권분석 API 수집기.

    SEOUL_API_KEY 가 비어있으면 더미 데이터를 반환해 개발·테스트를 지원한다.
    """

    def __init__(self) -> None:
        super().__init__(base_url=_BASE_URL, rate=2.0)
        self._key = settings.SEOUL_API_KEY
        self._dev_mode = not bool(self._key)
        if self._dev_mode:
            logger.warning(
                "SEOUL_API_KEY is not set — running in DEV mode (dummy data)."
            )

    def _url(self, service: str, start: int, end: int) -> str:
        return f"{_BASE_URL}/{self._key}/json/{service}/{start}/{end}/"

    def _url_template(self, service: str) -> str:
        return f"{_BASE_URL}/{self._key}/json/{service}/{{start}}/{{end}}/"

    # ── 1. 전체 상권 목록 ────────────────────────────────────────────────────

    async def get_all_commercial_areas(self) -> list[dict]:
        """
        골목·전통시장·발달상권·관광특구 전체 상권 목록.
        서비스: trdarRtarGetList
        """
        if self._dev_mode:
            return _DUMMY_AREAS

        rows = await self.get_all_pages(self._url_template("trdarRtarGetList"))
        logger.info("Fetched %d commercial areas", len(rows))
        return rows

    # ── 2. 추정매출 ──────────────────────────────────────────────────────────

    async def get_sales_data(self, area_cd: str, year_quarter: str) -> list[dict]:
        """
        상권 추정매출 조회.
        서비스: salesByIndustryCd
        """
        if self._dev_mode:
            return [{**_DUMMY_SALES_ROW, "TRDAR_CD": area_cd}]

        year, quarter = year_quarter[:4], year_quarter[-1]
        rows: list[dict] = []

        for start in range(1, 10001, 1000):
            url  = self._url("salesByIndustryCd", start, start + 999)
            data = await self.get(url)
            page_rows, total = parse_seoul_response(data)

            filtered = [
                r for r in page_rows
                if r.get("TRDAR_CD") == area_cd
                and r.get("STDR_YY_CD") == year
                and r.get("STDR_QU_CD") == quarter
            ]
            rows.extend(filtered)

            if not page_rows or (total > 0 and start + 999 >= total):
                break

        logger.info("Sales data: %d rows for %s %s", len(rows), area_cd, year_quarter)
        return rows

    # ── 3. 점포 현황 ─────────────────────────────────────────────────────────

    async def get_store_counts(self, area_cd: str, year_quarter: str) -> list[dict]:
        """
        상권 점포 현황.
        서비스: storeListInArea
        """
        if self._dev_mode:
            return [{**_DUMMY_STORE_ROW, "TRDAR_CD": area_cd}]

        year, quarter = year_quarter[:4], year_quarter[-1]
        rows: list[dict] = []

        for start in range(1, 10001, 1000):
            url  = self._url("storeListInArea", start, start + 999)
            data = await self.get(url)
            page_rows, total = parse_seoul_response(data)

            filtered = [
                r for r in page_rows
                if r.get("TRDAR_CD") == area_cd
                and r.get("STDR_YY_CD") == year
                and r.get("STDR_QU_CD") == quarter
            ]
            rows.extend(filtered)

            if not page_rows or (total > 0 and start + 999 >= total):
                break

        logger.info("Store counts: %d rows for %s %s", len(rows), area_cd, year_quarter)
        return rows

    # ── 4. 생활인구 ──────────────────────────────────────────────────────────

    async def get_resident_population(self, area_cd: str) -> list[dict]:
        """
        상권 생활인구 (전 분기 통합).
        서비스: residentCounts
        """
        if self._dev_mode:
            return [{**_DUMMY_POP_ROW, "TRDAR_CD": area_cd}]

        rows = await self.get_all_pages(self._url_template("residentCounts"))
        filtered = [r for r in rows if r.get("TRDAR_CD") == area_cd]
        logger.info("Resident population: %d rows for %s", len(filtered), area_cd)
        return filtered

    # ── 5. 직장인구 ──────────────────────────────────────────────────────────

    async def get_worker_population(self, area_cd: str) -> list[dict]:
        """
        상권 직장인구 (전 분기 통합).
        서비스: workerCounts
        """
        if self._dev_mode:
            return [{**_DUMMY_WORKER_ROW, "TRDAR_CD": area_cd}]

        rows = await self.get_all_pages(self._url_template("workerCounts"))
        filtered = [r for r in rows if r.get("TRDAR_CD") == area_cd]
        logger.info("Worker population: %d rows for %s", len(filtered), area_cd)
        return filtered

    # ── 6. 단일 상권 전체 수집 → DB 저장 ─────────────────────────────────────

    async def fetch_and_save(
        self,
        session: AsyncSession,
        area_cd: str,
        year_quarter: str = "2026Q1",
    ) -> int:
        """
        단일 상권(area_cd)의 4종 데이터를 병렬로 수집해 DB에 저장.

        Returns:
            저장된 레코드 수
        """
        logger.info("fetch_and_save start — area=%s quarter=%s", area_cd, year_quarter)

        # 병렬 API 호출
        results = await asyncio.gather(
            self.get_sales_data(area_cd, year_quarter),
            self.get_store_counts(area_cd, year_quarter),
            self.get_resident_population(area_cd),
            self.get_worker_population(area_cd),
            return_exceptions=True,
        )
        sales_rows, store_rows, pop_rows, worker_rows = results

        # CommercialArea 레코드 확인 (없으면 skip)
        result = await session.execute(
            select(CommercialArea).where(CommercialArea.area_cd == area_cd)
        )
        if result.scalar_one_or_none() is None:
            logger.warning("CommercialArea not found for area_cd=%s — skipping", area_cd)
            return 0

        objects: list[Any] = []

        # 매출 데이터
        if isinstance(sales_rows, Exception):
            logger.error("get_sales_data failed: %s", sales_rows)
        elif sales_rows:
            objects.extend(_map_sales(r) for r in sales_rows)

        # 점포 데이터
        if isinstance(store_rows, Exception):
            logger.error("get_store_counts failed: %s", store_rows)
        elif store_rows:
            objects.extend(_map_store(r) for r in store_rows)

        # 생활인구 데이터
        if isinstance(pop_rows, Exception):
            logger.error("get_resident_population failed: %s", pop_rows)
        elif pop_rows:
            objects.extend(_map_population(r) for r in pop_rows)

        # 직장인구 데이터
        if isinstance(worker_rows, Exception):
            logger.error("get_worker_population failed: %s", worker_rows)
        elif worker_rows:
            objects.extend(_map_worker(r) for r in worker_rows)

        if not objects:
            logger.info("No data to save for area=%s", area_cd)
            return 0

        try:
            session.add_all(objects)
            await session.commit()
            logger.info("Saved %d records for area=%s", len(objects), area_cd)
            return len(objects)
        except Exception as exc:
            await session.rollback()
            logger.error("DB save failed for area=%s: %s", area_cd, exc)
            raise


# ── API 행 → ORM 모델 매핑 ───────────────────────────────────────────────────

def _map_sales(row: dict) -> SalesData:
    return SalesData(
        area_cd=row["TRDAR_CD"],
        industry_cd=row.get("SVC_INDUTY_CD", ""),
        industry_nm=row.get("SVC_INDUTY_CD_NM", ""),
        year_quarter=_quarter(row),
        monthly_sales_avg=_int(row.get("MON_SELNG_AMT")),
        daily_sales_avg=_int(row.get("DAY_SELNG_AMT")),
        weekday_sales=_int(row.get("MDWK_SELNG_AMT")),
        weekend_sales=_int(row.get("WKND_SELNG_AMT")),
        time_slot_sales={
            "00-06": _int(row.get("TMZ_CD_01")),
            "06-11": _int(row.get("TMZ_CD_02")),
            "11-14": _int(row.get("TMZ_CD_03")),
            "14-17": _int(row.get("TMZ_CD_04")),
            "17-21": _int(row.get("TMZ_CD_05")),
            "21-24": _int(row.get("TMZ_CD_06")),
        },
    )


def _map_store(row: dict) -> StoreCount:
    return StoreCount(
        area_cd=row["TRDAR_CD"],
        year_quarter=_quarter(row),
        industry_cd=row.get("SVC_INDUTY_CD", ""),
        store_count=_int(row.get("STOR_CO")),
        open_rate=_float(row.get("OPR_RATE_RT")),
        close_rate=_float(row.get("CLR_RATE_RT")),
    )


def _map_population(row: dict) -> PopulationData:
    total = _int(row.get("TOT_FLPOP_CO"))
    male  = _int(row.get("ML_FLPOP_CO"))
    female = _int(row.get("FML_FLPOP_CO"))
    return PopulationData(
        area_cd=row["TRDAR_CD"],
        year_quarter=_quarter(row),
        total_population=total,
        age_10s=_int(row.get("AGRDE_10_FLPOP_CO")),
        age_20s=_int(row.get("AGRDE_20_FLPOP_CO")),
        age_30s=_int(row.get("AGRDE_30_FLPOP_CO")),
        age_40s=_int(row.get("AGRDE_40_FLPOP_CO")),
        age_50s=_int(row.get("AGRDE_50_FLPOP_CO")),
        age_60s=_int(row.get("AGRDE_60_ABOVE_FLPOP_CO")),
        male_ratio=round(male / total, 4) if total else 0.0,
        female_ratio=round(female / total, 4) if total else 0.0,
    )


def _map_worker(row: dict) -> WorkerPopulation:
    return WorkerPopulation(
        area_cd=row["TRDAR_CD"],
        year_quarter=_quarter(row),
        total_workers=_int(row.get("TOT_WRC_POPLTN_CO")),
        age_20s=_int(row.get("AGRDE_20_WRC_POPLTN_CO")),
        age_30s=_int(row.get("AGRDE_30_WRC_POPLTN_CO")),
        age_40s=_int(row.get("AGRDE_40_WRC_POPLTN_CO")),
        age_50s=_int(row.get("AGRDE_50_WRC_POPLTN_CO")),
    )
