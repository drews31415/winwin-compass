import asyncio
import logging
import math
from collections.abc import AsyncIterator
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
_PAGE_SIZE = 1000

SERVICE_AREAS = "TbgisTrdarRelm"
SERVICE_SALES = "VwsmTrdarSelngQq"
SERVICE_STORES = "VwsmTrdarStorQq"
SERVICE_FLOATING_POPULATION = "VwsmTrdarFlpopQq"
SERVICE_WORKER_POPULATION = "VwsmTrdarWrcPopltnQq"


def _int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val)) if val not in (None, "", " ") else default
    except (ValueError, TypeError):
        return default


def _float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val not in (None, "", " ") else default
    except (ValueError, TypeError):
        return default


def _quarter(row: dict) -> str:
    compact = str(row.get("STDR_YYQU_CD") or "")
    if len(compact) >= 5 and compact[:4].isdigit():
        return f"{compact[:4]}Q{compact[4]}"

    year = str(row.get("STDR_YY_CD") or "2024")
    quarter = str(row.get("STDR_QU_CD") or "3")
    return f"{year}Q{quarter}"


def quarter_to_seoul_code(year_quarter: str) -> str:
    return f"{year_quarter[:4]}{year_quarter[-1]}"


def _first_value(row: dict, *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, "", " "):
            return value
    return None


def _tm_to_wgs84(x_value: Any, y_value: Any) -> tuple[float | None, float | None]:
    """Convert Seoul's Korea 2000 central belt TM coordinates to WGS84 lon/lat."""
    x = _float(x_value, math.nan)
    y = _float(y_value, math.nan)
    if math.isnan(x) or math.isnan(y):
        return None, None

    a = 6378137.0
    f = 1 / 298.257222101
    e2 = 2 * f - f * f
    ep2 = e2 / (1 - e2)
    lat0 = math.radians(38.0)
    lon0 = math.radians(127.0)
    false_easting = 200000.0
    false_northing = 500000.0
    scale = 1.0

    def meridian_arc(phi: float) -> float:
        return a * (
            (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi
            - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * phi)
            + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * phi)
            - (35 * e2**3 / 3072) * math.sin(6 * phi)
        )

    m0 = meridian_arc(lat0)
    m = m0 + (y - false_northing) / scale
    mu = m / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))

    fp = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
        + (1097 * e1**4 / 512) * math.sin(8 * mu)
    )

    sin_fp = math.sin(fp)
    cos_fp = math.cos(fp)
    tan_fp = math.tan(fp)
    c1 = ep2 * cos_fp**2
    t1 = tan_fp**2
    n1 = a / math.sqrt(1 - e2 * sin_fp**2)
    r1 = a * (1 - e2) / (1 - e2 * sin_fp**2) ** 1.5
    d = (x - false_easting) / (n1 * scale)

    lat = fp - (n1 * tan_fp / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * ep2) * d**4 / 24
        + (
            61
            + 90 * t1
            + 298 * c1
            + 45 * t1**2
            - 252 * ep2
            - 3 * c1**2
        )
        * d**6
        / 720
    )
    lon = lon0 + (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (
            5
            - 2 * c1
            + 28 * t1
            - 3 * c1**2
            + 8 * ep2
            + 24 * t1**2
        )
        * d**5
        / 120
    ) / cos_fp

    return round(math.degrees(lon), 7), round(math.degrees(lat), 7)


_DUMMY_AREAS = [
    {
        "TRDAR_CD": "DEV001",
        "TRDAR_CD_NM": "테스트골목상권",
        "TRDAR_SE_CD_NM": "골목상권",
        "X_COORDINATE": "126.9784",
        "Y_COORDINATE": "37.5665",
        "SIGNGU_CD_NM": "중구",
    },
    {
        "TRDAR_CD": "DEV002",
        "TRDAR_CD_NM": "테스트전통시장",
        "TRDAR_SE_CD_NM": "전통시장",
        "X_COORDINATE": "126.9230",
        "Y_COORDINATE": "37.5547",
        "SIGNGU_CD_NM": "종로구",
    },
]

_DUMMY_SALES_ROW = {
    "STDR_YYQU_CD": "20254",
    "TRDAR_CD": "DEV001",
    "SVC_INDUTY_CD": "CS100001",
    "SVC_INDUTY_CD_NM": "한식음식점",
    "THSMON_SELNG_AMT": "15000000",
    "MDWK_SELNG_AMT": "9000000",
    "WKEND_SELNG_AMT": "6000000",
}

_DUMMY_STORE_ROW = {
    "STDR_YYQU_CD": "20254",
    "TRDAR_CD": "DEV001",
    "SVC_INDUTY_CD": "CS100001",
    "STOR_CO": "42",
    "OPBIZ_RT": "3.2",
    "CLSBIZ_RT": "2.1",
}

_DUMMY_POP_ROW = {
    "STDR_YYQU_CD": "20254",
    "TRDAR_CD": "DEV001",
    "TOT_FLPOP_CO": "12000",
    "AGRDE_10_FLPOP_CO": "800",
    "AGRDE_20_FLPOP_CO": "2800",
    "AGRDE_30_FLPOP_CO": "3100",
    "AGRDE_40_FLPOP_CO": "2500",
    "AGRDE_50_FLPOP_CO": "1900",
    "AGRDE_60_ABOVE_FLPOP_CO": "900",
    "ML_FLPOP_CO": "5800",
    "FML_FLPOP_CO": "6200",
}

_DUMMY_WORKER_ROW = {
    "STDR_YYQU_CD": "20254",
    "TRDAR_CD": "DEV001",
    "TOT_WRC_POPLTN_CO": "3500",
    "AGRDE_20_WRC_POPLTN_CO": "700",
    "AGRDE_30_WRC_POPLTN_CO": "1100",
    "AGRDE_40_WRC_POPLTN_CO": "950",
    "AGRDE_50_WRC_POPLTN_CO": "600",
}


class SeoulOpenAPI(BaseCollector):
    """Collector for Seoul commercial-area public data APIs."""

    def __init__(self) -> None:
        super().__init__(base_url=_BASE_URL, rate=2.0)
        self._key = settings.SEOUL_API_KEY
        self._dev_mode = not bool(self._key)
        if self._dev_mode:
            logger.warning("SEOUL_API_KEY is not set; running in dummy-data mode.")

    def _url(self, service: str, start: int, end: int) -> str:
        return f"{_BASE_URL}/{self._key}/json/{service}/{start}/{end}/"

    def _url_template(self, service: str) -> str:
        return f"{_BASE_URL}/{self._key}/json/{service}/{{start}}/{{end}}/"

    async def iter_pages(self, service: str) -> AsyncIterator[tuple[list[dict], int]]:
        start = 1
        total = 0
        while True:
            end = start + _PAGE_SIZE - 1
            data = await self.get(self._url(service, start, end))
            page_rows, total = parse_seoul_response(data)
            if not page_rows:
                break
            yield page_rows, total
            if total > 0 and end >= total:
                break
            start += _PAGE_SIZE

    async def get_all_commercial_areas(self) -> list[dict]:
        if self._dev_mode:
            return _DUMMY_AREAS

        rows = await self.get_all_pages(self._url_template(SERVICE_AREAS))
        logger.info("Fetched %d commercial areas", len(rows))
        return rows

    async def get_latest_quarter(self, service: str = SERVICE_STORES) -> str:
        if self._dev_mode:
            return "2025Q4"

        data = await self.get(self._url(service, 1, 1))
        rows, _ = parse_seoul_response(data)
        if not rows:
            raise RuntimeError(f"No Seoul API rows found for {service}")
        return _quarter(rows[0])

    async def get_sales_data(self, area_cd: str, year_quarter: str) -> list[dict]:
        if self._dev_mode:
            return [{**_DUMMY_SALES_ROW, "TRDAR_CD": area_cd}]

        target = quarter_to_seoul_code(year_quarter)
        rows: list[dict] = []
        async for page_rows, _ in self.iter_pages(SERVICE_SALES):
            rows.extend(
                r
                for r in page_rows
                if r.get("TRDAR_CD") == area_cd and str(r.get("STDR_YYQU_CD")) == target
            )
        logger.info("Sales data: %d rows for %s %s", len(rows), area_cd, year_quarter)
        return rows

    async def get_store_counts(self, area_cd: str, year_quarter: str) -> list[dict]:
        if self._dev_mode:
            return [{**_DUMMY_STORE_ROW, "TRDAR_CD": area_cd}]

        target = quarter_to_seoul_code(year_quarter)
        rows: list[dict] = []
        async for page_rows, _ in self.iter_pages(SERVICE_STORES):
            rows.extend(
                r
                for r in page_rows
                if r.get("TRDAR_CD") == area_cd and str(r.get("STDR_YYQU_CD")) == target
            )
        logger.info("Store counts: %d rows for %s %s", len(rows), area_cd, year_quarter)
        return rows

    async def get_resident_population(self, area_cd: str) -> list[dict]:
        if self._dev_mode:
            return [{**_DUMMY_POP_ROW, "TRDAR_CD": area_cd}]

        rows: list[dict] = []
        async for page_rows, _ in self.iter_pages(SERVICE_FLOATING_POPULATION):
            rows.extend(r for r in page_rows if r.get("TRDAR_CD") == area_cd)
        logger.info("Floating population: %d rows for %s", len(rows), area_cd)
        return rows

    async def get_worker_population(self, area_cd: str) -> list[dict]:
        if self._dev_mode:
            return [{**_DUMMY_WORKER_ROW, "TRDAR_CD": area_cd}]

        rows: list[dict] = []
        async for page_rows, _ in self.iter_pages(SERVICE_WORKER_POPULATION):
            rows.extend(r for r in page_rows if r.get("TRDAR_CD") == area_cd)
        logger.info("Worker population: %d rows for %s", len(rows), area_cd)
        return rows

    async def fetch_and_save(
        self,
        session: AsyncSession,
        area_cd: str,
        year_quarter: str = "2025Q4",
    ) -> int:
        logger.info("fetch_and_save start: area=%s quarter=%s", area_cd, year_quarter)

        results = await asyncio.gather(
            self.get_sales_data(area_cd, year_quarter),
            self.get_store_counts(area_cd, year_quarter),
            self.get_resident_population(area_cd),
            self.get_worker_population(area_cd),
            return_exceptions=True,
        )
        sales_rows, store_rows, pop_rows, worker_rows = results

        result = await session.execute(
            select(CommercialArea).where(CommercialArea.area_cd == area_cd)
        )
        if result.scalar_one_or_none() is None:
            logger.warning("CommercialArea not found for area_cd=%s; skipping", area_cd)
            return 0

        objects: list[Any] = []

        if isinstance(sales_rows, Exception):
            logger.error("get_sales_data failed: %s", sales_rows)
        elif sales_rows:
            objects.extend(_map_sales(r) for r in sales_rows)

        if isinstance(store_rows, Exception):
            logger.error("get_store_counts failed: %s", store_rows)
        elif store_rows:
            objects.extend(_map_store(r) for r in store_rows)

        if isinstance(pop_rows, Exception):
            logger.error("get_resident_population failed: %s", pop_rows)
        elif pop_rows:
            objects.extend(_map_population(r) for r in pop_rows)

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
        except Exception:
            await session.rollback()
            logger.exception("DB save failed for area=%s", area_cd)
            raise


def map_area(row: dict) -> CommercialArea:
    lng = _first_value(row, "X_COORDINATE", "LON", "LONGITUDE")
    lat = _first_value(row, "Y_COORDINATE", "LAT", "LATITUDE")

    if lng is None or lat is None:
        lng, lat = _tm_to_wgs84(row.get("XCNTS_VALUE"), row.get("YDNTS_VALUE"))

    return CommercialArea(
        area_cd=str(row["TRDAR_CD"]),
        area_nm=row.get("TRDAR_CD_NM", ""),
        gu_nm=row.get("SIGNGU_CD_NM", ""),
        area_type=row.get("TRDAR_SE_CD_NM", ""),
        geom_lng=_float(lng, None),
        geom_lat=_float(lat, None),
    )


def _map_sales(row: dict) -> SalesData:
    return SalesData(
        area_cd=str(row["TRDAR_CD"]),
        industry_cd=row.get("SVC_INDUTY_CD", ""),
        industry_nm=row.get("SVC_INDUTY_CD_NM", ""),
        year_quarter=_quarter(row),
        monthly_sales_avg=_int(
            _first_value(row, "MON_SELNG_AMT", "THSMON_SELNG_AMT")
        ),
        daily_sales_avg=_int(_first_value(row, "DAY_SELNG_AMT", "THSMON_SELNG_CO")),
        weekday_sales=_int(row.get("MDWK_SELNG_AMT")),
        weekend_sales=_int(_first_value(row, "WKND_SELNG_AMT", "WKEND_SELNG_AMT")),
        time_slot_sales={
            "00-06": _int(_first_value(row, "TMZON_00_06_SELNG_AMT", "TMZ_CD_01")),
            "06-11": _int(_first_value(row, "TMZON_06_11_SELNG_AMT", "TMZ_CD_02")),
            "11-14": _int(_first_value(row, "TMZON_11_14_SELNG_AMT", "TMZ_CD_03")),
            "14-17": _int(_first_value(row, "TMZON_14_17_SELNG_AMT", "TMZ_CD_04")),
            "17-21": _int(_first_value(row, "TMZON_17_21_SELNG_AMT", "TMZ_CD_05")),
            "21-24": _int(_first_value(row, "TMZON_21_24_SELNG_AMT", "TMZ_CD_06")),
        },
    )


def _map_store(row: dict) -> StoreCount:
    return StoreCount(
        area_cd=str(row["TRDAR_CD"]),
        year_quarter=_quarter(row),
        industry_cd=row.get("SVC_INDUTY_CD", ""),
        store_count=_int(row.get("STOR_CO")),
        open_rate=_float(_first_value(row, "OPBIZ_RT", "OPR_RATE_RT")),
        close_rate=_float(_first_value(row, "CLSBIZ_RT", "CLR_RATE_RT")),
    )


def _map_population(row: dict) -> PopulationData:
    total = _int(row.get("TOT_FLPOP_CO"))
    male = _int(row.get("ML_FLPOP_CO"))
    female = _int(row.get("FML_FLPOP_CO"))
    return PopulationData(
        area_cd=str(row["TRDAR_CD"]),
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
        area_cd=str(row["TRDAR_CD"]),
        year_quarter=_quarter(row),
        total_workers=_int(row.get("TOT_WRC_POPLTN_CO")),
        age_20s=_int(row.get("AGRDE_20_WRC_POPLTN_CO")),
        age_30s=_int(row.get("AGRDE_30_WRC_POPLTN_CO")),
        age_40s=_int(row.get("AGRDE_40_WRC_POPLTN_CO")),
        age_50s=_int(row.get("AGRDE_50_WRC_POPLTN_CO")),
    )
