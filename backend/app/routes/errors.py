from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain import InvalidTransition, NotFound


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # The brief wants 400 with field-level errors; FastAPI's default is 422.
        detail = []
        for e in exc.errors():
            # ('body', 'location') -> "location"; a bare offset like ('body', 5)
            # from a malformed JSON document has no field name -> "body".
            parts = [p for p in e["loc"] if p not in ("body", "query", "path")]
            if len(parts) == 1 and not isinstance(parts[0], str):
                field = "body"
            else:
                field = ".".join(str(p) for p in parts)
            detail.append({"field": field, "message": e["msg"]})
        return JSONResponse(status_code=400, content={"detail": detail})

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InvalidTransition)
    async def _conflict(_: Request, exc: InvalidTransition) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
