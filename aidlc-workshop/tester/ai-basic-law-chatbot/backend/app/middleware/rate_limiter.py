import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, HTTPException
from app.config import settings


class SlidingWindowRateLimiter:
    """슬라이딩 윈도우 알고리즘 기반 IP Rate Limiter (인메모리)."""

    def __init__(self, max_requests: int = 5, window_seconds: int = 600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._request_log: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        """현재 요청이 허용되는지 확인하고, 허용 시 타임스탬프 기록."""
        now = time.time()
        window_start = now - self.window_seconds

        self._request_log[ip] = [
            ts for ts in self._request_log[ip] if ts > window_start
        ]

        if len(self._request_log[ip]) >= self.max_requests:
            return False

        self._request_log[ip].append(now)
        return True

    def get_retry_after(self, ip: str) -> int:
        """해당 IP의 가장 오래된 요청이 만료되기까지 남은 초."""
        if not self._request_log[ip]:
            return 0
        oldest = min(self._request_log[ip])
        return max(0, int(self.window_seconds - (time.time() - oldest)))


# 싱글턴 인스턴스
_limiter = SlidingWindowRateLimiter(
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(request: Request) -> None:
    """FastAPI 의존성: Rate Limit 초과 시 HTTP 429 반환."""
    ip = get_client_ip(request)
    if not _limiter.is_allowed(ip):
        retry_after = _limiter.get_retry_after(ip)
        raise HTTPException(
            status_code=429,
            detail={
                "detail": "요청 한도를 초과했습니다. 10분 후에 다시 시도해주세요.",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
