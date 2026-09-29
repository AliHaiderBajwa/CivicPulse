import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from alembic.config import Config as AlembicConfig
from fastapi import FastAPI

from alembic import command
from app.config import Settings
from app.deps import get_engine, get_redis, get_settings
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware
from app.routes import complaints, health, meta, stats
from app.routes.errors import register_exception_handlers

log = logging.getLogger("app")

BACKEND_DIR = Path(__file__).resolve().parent.parent

DESCRIPTION = (
    "Municipal complaint intake, triage and operations API. "
    "Contract source: assignment PDF \u00a72.2 \u2014 both partners code against this file."
)


def apply_migrations() -> None:
    # alembic.ini uses %(here)s for script_location, so this works from any cwd
    # (compose, kind/CD, k8s-up.sh, uvicorn by hand) — DATABASE_URL is read by
    # alembic/env.py straight from the environment.
    command.upgrade(AlembicConfig(str(BACKEND_DIR / "alembic.ini")), "head")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("startup: migrating database to head")
    # Concurrency note: two replicas racing `upgrade head` on an empty DB is
    # benign — transactional DDL means the loser's transaction aborts, the
    # process exits non-zero, and the orchestrator restarts it; the retry then
    # no-ops at head.
    await asyncio.to_thread(apply_migrations)
    log.info("startup: database at head")
    yield
    # Runs after uvicorn has drained in-flight requests on SIGTERM.
    log.info("shutdown: closing connection pools")
    if get_engine.cache_info().currsize:
        get_engine().dispose()
    if get_redis.cache_info().currsize:
        get_redis().close()


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging((settings or get_settings()).log_level)
    app = FastAPI(
        title="CivicPulse API", version="1.0.0", description=DESCRIPTION, lifespan=lifespan
    )
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)
    app.include_router(complaints.router)
    app.include_router(stats.router)
    app.include_router(meta.router)
    app.include_router(health.router)
    return app


app = create_app()
