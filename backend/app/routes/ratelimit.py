from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.deps import get_rate_limiter
from app.services.rate_limiter import RateLimiter


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()      # first hop = the original client
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    request: Request,
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> None:
    decision = limiter.check(client_ip(request))
    if not decision.allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.",
                            headers={"Retry-After": str(decision.retry_after)})
