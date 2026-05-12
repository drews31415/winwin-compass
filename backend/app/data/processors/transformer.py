"""
상권 데이터 정제·분석 유틸리티.

  normalize_sales        — 서울 API 원시 응답 → 정규화 dict
  calculate_risk_score   — 폐업 위험 점수 (0~100)
  enrich_with_population — 매출 + 생활인구 결합
"""
from typing import Any


# ── 타입 변환 헬퍼 ────────────────────────────────────────────────────────────

def _to_int(val: Any, default: int = 0) -> int:
    try:
        return int(val) if val not in (None, "", " ") else default
    except (ValueError, TypeError):
        return default


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val) if val not in (None, "", " ") else default
    except (ValueError, TypeError):
        return default


def _year_quarter(row: dict) -> str:
    """STDR_YY_CD + STDR_QU_CD → '2024Q3' 포맷 통일."""
    yq = str(row.get("year_quarter", ""))
    if len(yq) == 6 and "Q" in yq:
        return yq  # 이미 정규화됨

    year    = str(row.get("STDR_YY_CD") or row.get("year", "2024"))
    quarter = str(row.get("STDR_QU_CD") or row.get("quarter", "1"))
    return f"{year}Q{quarter}"


# ── 1. 매출 데이터 정규화 ─────────────────────────────────────────────────────

def normalize_sales(raw: dict) -> dict:
    """
    서울 열린데이터 API 원시 응답 행 → sales_data 스키마 dict 변환.

    - 숫자형 필드: 문자열 → int
    - None/빈값: 기본값 0 처리
    - year_quarter: '2024Q3' 포맷 통일
    """
    return {
        "area_cd":          str(raw.get("TRDAR_CD")        or raw.get("area_cd", "")),
        "industry_cd":      str(raw.get("SVC_INDUTY_CD")   or raw.get("industry_cd", "")),
        "industry_nm":      str(raw.get("SVC_INDUTY_CD_NM") or raw.get("industry_nm", "")),
        "year_quarter":     _year_quarter(raw),
        "monthly_sales_avg": _to_int(raw.get("MON_SELNG_AMT")  or raw.get("monthly_sales_avg")),
        "daily_sales_avg":   _to_int(raw.get("DAY_SELNG_AMT")  or raw.get("daily_sales_avg")),
        "weekday_sales":     _to_int(raw.get("MDWK_SELNG_AMT") or raw.get("weekday_sales")),
        "weekend_sales":     _to_int(raw.get("WKND_SELNG_AMT") or raw.get("weekend_sales")),
        "time_slot_sales": (
            {
                "00-06": _to_int(raw.get("TMZ_CD_01")),
                "06-11": _to_int(raw.get("TMZ_CD_02")),
                "11-14": _to_int(raw.get("TMZ_CD_03")),
                "14-17": _to_int(raw.get("TMZ_CD_04")),
                "17-21": _to_int(raw.get("TMZ_CD_05")),
                "21-24": _to_int(raw.get("TMZ_CD_06")),
            }
            if "TMZ_CD_01" in raw
            else raw.get("time_slot_sales", {})
        ),
    }


# ── 2. 폐업 위험 점수 계산 ────────────────────────────────────────────────────

# 각 지표의 "위험 포화값" — 이 수치 이상이면 해당 항목 100점
_CLOSE_RATE_MAX    = 15.0  # 폐업률 15% 이상
_SALES_DECLINE_MAX = 30.0  # 매출 감소율 30% 이상
_STORE_GROWTH_MAX  = 20.0  # 점포 증가율 20% 이상 (경쟁 심화)

_W_CLOSE   = 0.40
_W_SALES   = 0.35
_W_COMPETE = 0.25


def calculate_risk_score(store_data: dict, sales_data: dict) -> float:
    """
    폐업 위험 점수를 0~100 float으로 반환. 점수가 높을수록 위험.

    가중치:
      폐업률              40%
      매출 감소율          35%
      점포 증가율(경쟁심화) 25%

    Args:
        store_data: StoreCount 기반 dict.
                    필드: close_rate(float), store_count(int),
                          prev_store_count(int, 선택 — 없으면 경쟁 점수 0)
        sales_data: SalesData 기반 dict.
                    필드: monthly_sales_avg(int),
                          prev_monthly_sales_avg(int, 선택 — 없으면 매출 감소 점수 0)
    """
    # ── 폐업률 점수 ──────────────────────────────────────────────
    close_rate  = _to_float(store_data.get("close_rate"))
    close_score = min(close_rate / _CLOSE_RATE_MAX, 1.0) * 100

    # ── 매출 감소율 점수 ─────────────────────────────────────────
    current_sales = _to_int(sales_data.get("monthly_sales_avg"))
    prev_sales    = _to_int(sales_data.get("prev_monthly_sales_avg"))

    if prev_sales > 0 and current_sales < prev_sales:
        decline_rate = (prev_sales - current_sales) / prev_sales * 100
        sales_score  = min(decline_rate / _SALES_DECLINE_MAX, 1.0) * 100
    else:
        sales_score = 0.0

    # ── 점포 증가율 점수 (경쟁 심화) ────────────────────────────
    current_stores = _to_int(store_data.get("store_count"))
    prev_stores    = _to_int(store_data.get("prev_store_count"))

    if prev_stores > 0 and current_stores > prev_stores:
        growth_rate   = (current_stores - prev_stores) / prev_stores * 100
        compete_score = min(growth_rate / _STORE_GROWTH_MAX, 1.0) * 100
    else:
        compete_score = 0.0

    risk = (
        _W_CLOSE   * close_score
        + _W_SALES   * sales_score
        + _W_COMPETE * compete_score
    )
    return round(risk, 2)


# ── 3. 매출 + 생활인구 결합 ───────────────────────────────────────────────────

# 연령대별 소비 성향 가중치 (합산 1.0, 통계청 가계동향조사 참고)
_AGE_WEIGHTS: dict[str, float] = {
    "age_10s": 0.05,
    "age_20s": 0.25,
    "age_30s": 0.28,
    "age_40s": 0.22,
    "age_50s": 0.14,
    "age_60s": 0.06,
}


def enrich_with_population(sales: dict, population: dict) -> dict:
    """
    매출 데이터와 생활인구 데이터를 결합해 분석 지표를 추가한다.

    Args:
        sales:      normalize_sales() 반환값 또는 SalesData dict
        population: PopulationData dict
                    필드: total_population, age_10s ~ age_60s

    Returns:
        sales에 다음 필드가 추가된 dict:
          total_population       — 생활인구 총계
          sales_per_capita       — 1인당 월 매출 (원)
          age_sales_contribution — 연령대별 추정 매출 기여 비율 dict
    """
    total_pop   = _to_int(population.get("total_population"))
    monthly_avg = _to_int(sales.get("monthly_sales_avg"))

    sales_per_capita = round(monthly_avg / total_pop) if total_pop > 0 else 0

    # 인구 비율 × 소비 성향 가중치 → 기여도 추정, 합계 1.0으로 정규화
    raw_contrib: dict[str, float] = {}
    for age_key, weight in _AGE_WEIGHTS.items():
        age_pop   = _to_int(population.get(age_key))
        pop_ratio = age_pop / total_pop if total_pop > 0 else 0.0
        raw_contrib[age_key] = pop_ratio * weight

    total_weight = sum(raw_contrib.values())
    age_contribution = (
        {k: round(v / total_weight, 4) for k, v in raw_contrib.items()}
        if total_weight > 0
        else {k: 0.0 for k in _AGE_WEIGHTS}
    )

    return {
        **sales,
        "total_population":       total_pop,
        "sales_per_capita":       sales_per_capita,
        "age_sales_contribution": age_contribution,
    }
