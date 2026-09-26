import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.logging_config import request_id_var
from app.metrics import HTTP_LATENCY, HTTP_REQUESTS

log = logging.getLogger("app.access")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope["headers"])
        rid = headers.get(b"x-request-id", b"").decode() or uuid.uuid4().hex
        token = request_id_var.set(rid)
        started = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                message["headers"] = [
                    *message.get("headers", []),
                    (b"x-request-id", rid.encode()),
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - started
            route = scope.get("route")
            # Route template, not the raw URL: keeps metric label cardinality bounded.
            path = getattr(route, "path", None) or scope["path"]
            HTTP_REQUESTS.labels(scope["method"], path, str(status["code"])).inc()
            HTTP_LATENCY.labels(scope["method"], path).observe(elapsed)
            log.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status["code"],
                    "duration_ms": round(elapsed * 1000, 1),
                },
            )
            request_id_var.reset(token)
