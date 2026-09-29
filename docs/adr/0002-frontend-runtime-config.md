# ADR 0002: Frontend backend address via runtime envsubst, never build-time baking

- **Status:** Accepted, 2026-09-25
- **Authors:** Ali Haider Bajwa (with opencode, disclosed in `docs/AI-USAGE.md`)
- **Context:** CS4032 Assignment 1 brief — one frontend image must serve
  local Compose, the ephemeral kind cluster in CI, and any preview, each
  pointing at a *different* backend address.

## Context

The React client calls the API over relative paths (`/api/...`), so the
browser never hardcodes a host — but *something* must terminate `/api` and
forward it. That something is the nginx shipped inside the frontend image,
and the backend address differs per environment (`backend:8000` in Compose,
the cluster Ingress in kind). The question is when `BACKEND_URL` gets bound:
at image build time or at container start time.

## Decision

**Bind it at container start time, with a default that works for Compose.**

- `frontend/nginx.conf` is a *template*: `proxy_pass http://${BACKEND_URL}`
  (`nginx.conf:26`), processed by the image entrypoint's envsubst step
  (`/etc/nginx/templates/*.template` → `/etc/nginx/conf.d/`,
  `nginx.conf:1-3`).
- The Dockerfile ships the template and a default —
  `COPY nginx.conf /etc/nginx/templates/default.conf.template` plus
  `ENV BACKEND_URL=backend:8000` (`frontend/Dockerfile:32-38`) — so an
  unconfigured `docker compose up` works with zero environment setup.
- The same image therefore serves every environment: Compose relies on the
  default, kind/CD overrides it per overlay, and no rebuild is ever needed
  to repoint the API.

## Alternatives considered

- **Build-time `VITE_*` baking.** The standard Vite pattern, but it bakes
  one backend address into the bundle: N environments need N images, and a
  stale-env image serves the wrong API silently. Directly contradicts the
  build-once-deploy-many rule (ADR 0003).
- **Serve the SPA from the backend.** Removes the proxy question, but fuses
  two independently-scalable deployables into one and puts static traffic
  on Python workers.
- **Hardcoded per-env URLs in `client.ts`.** No.

## Consequences

- One frontend image for all environments; repointing is a container-restart
  affair, not a rebuild.
- A missing `BACKEND_URL` fails visibly at request time (empty upstream),
  not silently — mitigated by the Compose-correct default and by every
  manifest/Compose file setting it explicitly.
- The proxy preserves the client chain the backend bills on:
  `X-Forwarded-For` chaining and `X-Request-ID` passthrough live in the same
  `location /api/` block (`nginx.conf:26-35`), so the rate limiter's
  per-client accounting survives the hop.
