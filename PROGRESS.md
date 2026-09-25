# PROGRESS — CivicPulse

Living log. One entry per milestone: **Expected / Achieved / Evidence / Next**.
Regenerate the docx after every entry: `python3 scripts/build_docx.py`.

---

## M0 — Process bootstrap (Ali + AI agent)

**Expected:** Repo initialized safely; plan of record in-repo; process docs (this file, rubric checklist, assignment brief, docx pipeline) exist; `.env` can never be committed.

**Achieved:**
- Repo `AliHaiderBajwa/CivicPulse` (public) cloned; `dev` branch created; git identity = Ali Haider Bajwa.
- Root commit `423b8b3` = `.gitignore` + `.env.example` **only** — `.env` ignored from commit one (`git check-ignore` verified).
- Local `.env` holds the real Groq key; never staged.
- Pre-flight tools installed and verified: kubectl v1.37.1, k3d v5.9.0, kustomize v5.8.1, kubeconform v0.8.0, k6 v2.3.0, trivy v0.74.0, syft v1.52.0, helm v4.3.0, matplotlib 3.11.1.
- 48h plan audited against the PDF; 7 gaps (G1–G7) amended into `docs/PLAN.md`.
- AGENTS.md standing order: milestone → PROGRESS → docx → rubric tick.

**Evidence:** this file; `git log --oneline`; `git check-ignore -v .env`.

**Next:** Block 0 — repo layout, stub backend, contracts, Issues, docs skeleton.

---

## M1 — Block 0: contracts frozen (Ali + AI agent)

**Expected:** Repo layout, `.env.example`, OpenAPI contract both partners code against, stub backend for infra bring-up, 14 Issues, branch protection on `main`.

**Achieved:**
- `docs/openapi.json` authored from PDF §2.2 — all 9 contract routes + schemas (enums, field-level `ValidationError`, `X-Cache`/`Retry-After` headers documented).
- `tools/stub-backend/` (stdlib Python, non-root Dockerfile, /health · /ready · /api/stats with X-Cache MISS→HIT toggle) + `compose.stub.yaml` overlay for pre-integration runs.
- 14 Issues created (#1–#14) with workstream labels.
- `main` protected: PR required, 1 approval, force-push and deletion blocked (status checks to be added after first CI run). `README.md` bootstrapped; `main` created from `dev` — everything after this lands via PR.
- Service-name/port contract: `frontend` :8080 · `backend` :8000 · `database` · `cache` · `ollama`; GHCR images `ghcr.io/alihaiderbajwa/civicpulse-{backend,frontend}`.

**Evidence:** GitHub branch settings; `gh issue list`; `docs/openapi.json`.

**Next:** P2 frontend, P3 compose.

---

## M2 — P2: frontend complete (Ali + AI agent)

**Expected:** Submit/Dashboard/Stats views, typed client from OpenAPI, no baked-in API URL, 409 verbatim, X-Cache badge, error boundary, ≥5 Vitest tests, multi-stage non-root nginx image.

**Achieved:**
- React 18 + Vite + TS. `src/api/schema.d.ts` generated from `docs/openapi.json` via `openapi-typescript` (script `gen:api`). `client.ts` uses **relative `/api` URLs only** — grep-verified zero `VITE_`/absolute URLs.
- Submit (validation 10–2000 / 3–200, honest loading, renders category + priority + summary + **triaged_by**), Dashboard (pagination, 3 filters, all four statuses offered with **no transition table in the frontend**, 409 `detail` rendered verbatim), Stats (aggregates + **X-Cache badge**), ErrorBoundary.
- **15 Vitest tests pass** (submit/dashboard/stats/client/app files); gates verified independently by main session: `tsc --noEmit` ✓, `eslint` ✓, `vite build` ✓ (154 kB bundle).
- `frontend/Dockerfile`: `node:22-alpine` build → `nginx:1.27-alpine` serve, `USER nginx`, listens 8080, HEALTHCHECK, no node/source in final image (agent verified: `which node` → absent; image 73.9 MB… note: >60 MB target — revisit layering if time allows).
- `nginx.conf`: envsubst template `BACKEND_URL` (default `backend:8000`), `/api/` proxied **without** stripping the prefix, X-Forwarded-For set — works identically in Compose and K8s (ADR 0002).

**Evidence:** `frontend/tests/` (15 green); commit `caf6310`.

**Next:** P3 compose bring-up.

---

## M3 — P3: compose stack live + network segmentation proven (Ali + AI agent)

**Expected:** Both compose files (dev/prod), 2 networks with `internal: true`, 3 justified volumes, healthchecks + `service_healthy`, pinned images, no published DB/cache ports, and the failing `ping database` proof.

**Achieved:**
- `compose.yaml` (dev: build:, bind mount with G2 justification comment, backend :8000 published for dev only) · `compose.prod.yaml` (image `${IMAGE_TAG}` by `:?`-required SHA, **no build key**, no bind mount, counter-comment for G2, no published DB/cache/backend ports) · `compose.stub.yaml` (temporary, `!reset`s the bind mount).
- Pinned: `postgres:16-alpine`, `redis:7-alpine` (AOF `--appendonly yes`), `ollama/ollama:0.11.4` (profile-gated, on `edge` because it must download models).
- **Full stack healthy via `up --wait`**: db/cache → backend → frontend dependency chain observed in logs; all four containers healthy.
- **Segmentation proven:** `exec frontend ping database` → `ping: bad address` (and same for `cache`); frontend→backend over edge works; backend resolves db/cache AND `api.groq.com` (answers engineering note Q7: egress lives on `edge` where the backend bridges).
- **Request path green through the proxy:** `GET /api/stats` → `X-Cache: MISS` then `HIT`; `/api/complaints` list OK; SPA 200 on :8080.

**Evidence:** `docs/evidence/08-ping-fails.txt`; live curl output in session; commits `caf6310`, `5842674`.

**Next:** P4 `ci.yml` (then tick B5 + required status checks), watch for Ashar's backend PRs (Issues 1,3,4,5,6,10), P5 K8s.

<!-- New entries above this line. -->
