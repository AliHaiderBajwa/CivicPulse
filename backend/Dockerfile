# syntax=docker/dockerfile:1
FROM python:3.12.13-slim-bookworm AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Dependencies FIRST: this layer stays cached until the lockfile changes.
# --only-binary :all: : never execute a package setup script (docker:S8541).
# --require-hashes    : every wheel is matched against requirements.lock's SHA-256
#                       (docker:S8544); --no-deps: the lock is already the full closure.
COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary :all: --no-deps --require-hashes -r requirements.lock

FROM python:3.12.13-slim-bookworm AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# OS-level CVE fix first: Trivy flags 3 HIGHs in libpcre2-8-0 (10.42-1) shipped
# by the base image; 10.42-1+deb12u1 fixes all three. Runtime user created in the
# same layer (consecutive RUNs must merge, docker:S7031).
RUN apt-get update \
    && apt-get upgrade -y libpcre2-8-0 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=10001:10001 alembic.ini ./
COPY --chown=10001:10001 alembic ./alembic
# Source LAST: code edits don't invalidate the dependency layer above.
COPY --chown=10001:10001 app ./app
USER 10001:10001
EXPOSE 8000
# No curl in slim -> healthcheck via stdlib urllib.
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]
# Exec form: uvicorn is PID 1 and receives SIGTERM directly (shell form would swallow it).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--timeout-graceful-shutdown", "20"]
