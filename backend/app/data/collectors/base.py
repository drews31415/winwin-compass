import asyncio
import hashlib
import json
import logging
from typing import Any

import httpx
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_TTL = 6 * 3600   # 6시간
_PAGE_SIZE  = 1000       # 서울 열린데이터 페이지 크기


# ── Rate Limiter ─────────────────────────────────────────────────────────────

class RateLimiter:
    """Lock 기반 토큰 버킷 — 초당 N회 제한."""

    def __init__(self, rate: float = 2.0):
        self._interval = 1.0 / rate
        self._last: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_event_loop()
            now  = loop.time()
            gap  = self._interval - (now - self._last)
            if gap > 0:
                await asyncio.sleep(gap)
            self._last = loop.time()


# ── Base Collector ───────────────────────────────────────────────────────────

class BaseCollector:
    """
    공통 비동기 HTTP 클라이언트.

    - httpx.AsyncClient 세션 재사용
    - 지수 백오프 재시도 (최대 3회: 1s → 2s → 4s)
    - Redis 응답 캐시 (TTL 6시간)
    - Rate Limiter (기본 초당 2회)
    """

    def __init__(self, base_url: str, rate: float = 2.0):
        self.base_url   = base_url.rstrip("/")
        self._client:  httpx.AsyncClient | None = None
        self._redis:   aioredis.Redis    | None = None
        self._limiter  = RateLimiter(rate)

    # ── 내부 리소스 ──────────────────────────────────────────────────────────

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
                follow_redirects=True,
            )
        return self._client

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(
                settings.REDIS_URL, encoding="utf-8", decode_responses=True
            )
        return self._redis

    # ── 캐시 헬퍼 ────────────────────────────────────────────────────────────

    @staticmethod
    def _make_cache_key(url: str, params: dict | None) -> str:
        raw = url + json.dumps(params or {}, sort_keys=True)
        return "golmok:http:" + hashlib.sha1(raw.encode()).hexdigest()

    async def _cache_get(self, key: str) -> dict | None:
        try:
            redis  = await self._get_redis()
            cached = await redis.get(key)
            return json.loads(cached) if cached else None
        except Exception as exc:
            logger.warning("Redis GET failed (key=%s): %s", key, exc)
            return None

    async def _cache_set(self, key: str, data: dict) -> None:
        try:
            redis = await self._get_redis()
            await redis.setex(key, _CACHE_TTL, json.dumps(data, ensure_ascii=False))
        except Exception as exc:
            logger.warning("Redis SET failed (key=%s): %s", key, exc)

    # ── HTTP GET ─────────────────────────────────────────────────────────────

    async def get(
        self,
        url: str,
        params: dict | None = None,
        *,
        use_cache: bool = True,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """단일 GET 요청 — 캐시 우선 조회 후 재시도 포함."""
        cache_key = self._make_cache_key(url, params)

        if use_cache:
            cached = await self._cache_get(cache_key)
            if cached is not None:
                logger.debug("Cache HIT: %s", url)
                return cached

        client    = await self._get_client()
        last_exc: Exception | None = None

        for attempt in range(1, max_retries + 1):
            await self._limiter.wait()
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
                if use_cache:
                    await self._cache_set(cache_key, data)
                return data

            except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as exc:
                last_exc = exc
                backoff  = 2 ** (attempt - 1)   # 1s, 2s, 4s
                logger.warning(
                    "Attempt [%d/%d] failed — %s: %s. backoff=%ds",
                    attempt, max_retries, url, exc, backoff,
                )
                if attempt < max_retries:
                    await asyncio.sleep(backoff)

        logger.error("All %d retries exhausted: %s", max_retries, url)
        raise last_exc  # type: ignore[misc]

    # ── 페이지네이션 ──────────────────────────────────────────────────────────

    async def get_all_pages(self, url_template: str) -> list[dict]:
        """
        서울 열린데이터 페이지네이션 자동 처리.

        url_template 에 {start}/{end} 플레이스홀더 포함 필요.
        예) "http://openapi.seoul.go.kr:8088/KEY/json/salesByIndustryCd/{start}/{end}/"
        """
        rows: list[dict] = []
        start = 1

        while True:
            end  = start + _PAGE_SIZE - 1
            url  = url_template.format(start=start, end=end)
            data = await self.get(url)

            page_rows, total = parse_seoul_response(data)
            rows.extend(page_rows)

            if not page_rows or (total > 0 and len(rows) >= total):
                break
            start += _PAGE_SIZE

        return rows

    # ── 컨텍스트 매니저 ──────────────────────────────────────────────────────

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._redis:
            await self._redis.aclose()

    async def __aenter__(self) -> "BaseCollector":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


# ── 서울 열린데이터 공통 응답 파서 ───────────────────────────────────────────

def parse_seoul_response(data: dict) -> tuple[list[dict], int]:
    """
    최상위 서비스 키를 꺼내 (rows, total_count) 를 반환.

    결과 코드:
      INFO-000 → 정상
      INFO-200 → 데이터 없음 (빈 리스트 반환)
      그 외     → 경고 로그 후 빈 리스트 반환
    """
    if not data:
        return [], 0

    service_key = next(iter(data))
    payload     = data[service_key]

    result      = payload.get("RESULT", {})
    code        = result.get("CODE", "INFO-000")

    if code == "INFO-200":
        logger.debug("Seoul API returned empty result (INFO-200)")
        return [], 0

    if not code.startswith("INFO-000"):
        logger.warning("Seoul API error — code=%s msg=%s", code, result.get("MESSAGE"))
        return [], 0

    rows  = payload.get("row", [])
    total = int(payload.get("list_total_count", len(rows)))
    return rows, total
