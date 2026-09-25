# Handoff for Ashar — backend, data, cache and AI layer

Written by Ali's AI agent (disclosed in `docs/AI-USAGE.md`) so you can start
without waiting for a call. Everything in this file is **yours**; nothing here
has been implemented for you on purpose. The frontend, Compose, Kubernetes and
CI/CD are Ali's and are done — you build on top of them.

You are `@ashar1x` and Ali has added you to the repo as a collaborator with push
access, so you can branch and open PRs straight away. Ali's AI agent has also
assigned your issues to you (visible as assignee on each). Read this, then work
them in order.

**Current state (so you know exactly what you are starting from):** 24 commits,
all Ali's; CI green on 7 required checks; CD green end to end
(build → publish → deploy-k8s, run `36170624771`, deployed by commit SHA to an
ephemeral kind cluster with a 201 through the Ingress); local k3d cluster up via
`scripts/k8s-up.sh`; frontend, Compose, Kubernetes and CI/CD finished. Your code
is the missing ~50% of the marks (brief §6 values the AI layer and backend at 25
each). Nothing in your scope has been started, by Ali or by the agent.

---

## 1. What is already done, so you do not rebuild it

| Area | State | Where |
|---|---|---|
| API contract | Frozen OpenAPI 3.1, 7 paths | `docs/openapi.json` |
| Typed frontend client | Generated from the contract; your schema must not drift | `frontend/src/api/client.ts` |
| Compose stack | `postgres:16-alpine` + `redis:7-alpine`, healthchecks, internal networks, **no published DB/cache ports** | `compose.yaml` |
| Contract stub | In-memory HTTP server implementing the contract so the frontend/K8s could be built before you started. **Not production code, satisfies no rubric item** — replace it, do not port it | `tools/stub-backend/` |
| Kubernetes | Deployments, StatefulSet+volumeClaimTemplates, Redis PVC, Services, Ingress, HPA, VPA, PDB, dev/prod overlays | `k8s/` |
| CI | 7 required checks; `test-backend` **starts running the moment `backend/pyproject.toml` exists** | `.github/workflows/ci.yml` |
| CD | `build → publish → deploy-k8s`, deploys by commit SHA | `.github/workflows/cd.yml` |
| Local cluster | `scripts/k8s-up.sh` brings the whole stack up reproducibly | `scripts/k8s-up.sh` |
| Docs/evidence | Rubric checklist with your boxes still open, PROGRESS log, AI disclosure | `docs/RUBRIC-CHECKLIST.md`, `PROGRESS.md` |

Your code slots straight in: drop a real `backend/` directory in and both the CI
`test-backend` job and the CD `build` job switch from the stub to your image
automatically. No change needed from Ali.

## 2. Your issues, in dependency order

| # | Issue | Why this order |
|---|---|---|
| 1 | API skeleton + OpenAPI contract | Everything imports from your `app/` package |
| 3 | DB migration + idempotent seed | `/api/stats` and the dashboard need real rows |
| 4 | Triage providers + fallback + validation | Complaint POST depends on it |
| 5 | Complaint API + state machine + request logging | The 409 behaviour the frontend already renders |
| 6 | Redis stats cache + rate limiter | Last: pure optimisation on top of working endpoints |
| 10 | Backend test suite | Write alongside, but land the suite as its own PRs |
| 17 | Prometheus `/metrics` endpoint | The brief lists 9 endpoints; the frozen contract has 7. Add it when you re-export the schema |
| 18 | `TRIAGE.md` + your ENGINEERING-NOTES answers | Write these as you land the code so the `file:line` refs stay true |

## 3. The rules that will cost marks if you break them

These come from the PDF and from `AGENTS.md`:

1. **The fallback is the single most important behaviour in the whole project.**
   A provider that *always* raises must still let `POST /api/complaints` return
   **201**, with `triaged_by == "rules:fallback"`. A 500 here is an automatic
   deduction. It must be a real test in CI, not a claim in a README.
2. **Category and priority are closed sets.** `category` ∈ water, electricity,
   sanitation, roads, streetlights, other. `priority` ∈ high, normal, low.
   Anything else is a validation error, not a silent default.
3. **Invalid status transitions return 409, not 400 or 500.** The frontend
   already renders the 409 body, so keep the `{"detail": ...}` shape.
4. **`/health` vs `/ready` are different.** Liveness must not depend on
   Postgres/Redis; readiness must.
5. **10s timeout on the LLM call, at most one retry**, and only for
   timeout/429/5xx. Never retry a 400.
6. **Never log or return the LLM key.** It arrives from the environment
   (`LLM_API_KEY`), injected from GitHub Secrets in CD.
7. **No `:latest` anywhere**, no `localhost` between services (use `database`,
   `cache`), Postgres is a StatefulSet with a PVC, and DB/cache ports are never
   published.
8. **Service-to-service calls use K8s/Compose DNS names**, so the same image
   works in both.

## 4. Local setup

```bash
cp .env.example .env      # add your own LLM_API_KEY locally; never commit it
docker compose up -d --wait
cd backend && pytest      # your suite, must be >=14 tests, coverage >=65%
cd frontend && npm test   # Ali's suite — it must still pass against your API
```

The stub is what the frontend is pointed at today. When your backend is ready,
`compose.yaml` already prefers `backend/` over `tools/stub-backend/`; run
`docker compose up -d --build --wait` and confirm the frontend still renders
`GET /`, `GET /api/stats` and the 409 path.

## 5. Acceptance criteria per issue

- **#1** — `python -c "import app"` works; every path in `docs/openapi.json`
  exists; re-exporting the schema produces no diff against the committed file.
- **#3** — `alembic upgrade head` then `downgrade -1` then `upgrade head` all
  succeed; running the seed twice leaves the row count unchanged (uuid5 +
  `ON CONFLICT`); ≥30 seed complaints spread across all categories, priorities
  and statuses.
- **#4** — four providers behind one protocol (`llm`, `ollama`, `rules`,
  `simulated`); structured output validated with Pydantic; a content-hash cache;
  a prompt-injection guardrail; and the always-raise → 201 + `rules:fallback`
  test.
- **#5** — full endpoint parity with the contract; explicit transition table;
  409 on disallowed transitions; 400 with field-level detail on bad input; JSON
  logs carrying a `request_id`; SIGTERM drains in-flight requests.
- **#6** — `/api/stats` is a read-through cache with 30s TTL, returns
  `X-Cache: MISS` then `HIT`, and is invalidated on write; the POST rate limiter
  is distributed (Redis), returns 429 with `Retry-After`, and honours the PDF's
  10/minute per client in base and production.
- **#10** — ≥14 deterministic tests, no network calls, coverage ≥65% on `app/`.
- **#17 `/metrics`** — Prometheus text format exposing request count, latency
  histogram, triage latency and a fallback counter that increments exactly when a
  provider degrades to `rules:fallback`. Must not touch Postgres and must not be
  rate limited. The committed `docs/openapi.json` has no `/metrics`, so add it
  when you re-export the schema in #1 and regenerate `frontend/src/api/client.ts`.
- **#18 docs** — `TRIAGE.md` (four providers, `TRIAGE_PROVIDER` selection, JSON
  mode + Pydantic validation, 10s timeout, single jittered retry, content-hash
  cache with **measured hit rate**, injection guardrail, the always-raise test
  with its CI run link) plus your four ENGINEERING-NOTES answers with
  `file:line` refs.

## 6. Deliverables, and who signs each one

From the brief §4. The right-hand column is who has to produce it.

| Deliverable | Owner | State |
|---|---|---|
| README (problem, badges, Mermaid, one-command quickstart, API table, screenshots) | Ali | not started |
| 4 ADRs (provider interface, frontend runtime config, deploy-by-SHA, PII/data governance) | Ali (the provider-interface one needs your input) | not started |
| RUNBOOK (incl. `rollout undo` vs re-applying the previous SHA) | Ali | not started |
| ENGINEERING-NOTES — 8 questions, `file:line` refs | **split**: Ali does frontend runtime config, deploy-by-SHA, K8s probes/autoscaling, CI security; **you do** provider interface, retry policy, cache TTL + invalidation, fallback guarantees | not started |
| TRIAGE.md | **you** (issue #18) | not started |
| AI-USAGE.md | Ali (honest, specific) | done, updated every milestone |
| Demo video ≤5 min, **both partners speaking** | both of us — book it, do not leave it to the end | not started |
| `docs/evidence/` screenshots and captures | Ali (done, 21 files) | done |
| `scripts/check_submission.py` clean | Ali | not run yet |
| Submission bundle: repo URL, green `cd.yml` run link, both GHCR images with SHA tags, video link, `git shortlog -sn`, HPA capture + chart | Ali | 5 of 6 ready — **only the video link and a meaningful `git shortlog` are outstanding, and both need you** |

## 7. How to structure the work so both of us get the pair marks

The rubric wants genuine two-person work, and the numbers are not decorative:

- **≥35 commits each.** That is a lot of commits, so make them small and
  meaningful: one behaviour or one test per commit, conventional prefixes
  (`feat:`, `fix:`, `test:`, `docs:`). Do not squash your own history before
  submitting — Ali has been committing in small pieces for exactly this reason.
- **≥5 merged PRs each, with the other partner reviewing.** I will review your
  PRs and leave comments; please review mine too. Reviews from the other partner
  are what the rubric counts.
- **One deliberate merge conflict** that we resolve together, and document. The
  natural one: we will both touch `compose.yaml` (you add a healthcheck or env
  var for the backend, I adjust networks) or `docs/openapi.json`. Do it on a
  feature branch, don't fast-forward around it.
- **Review SLA:** the plan says partner reviews within 15 minutes. I will be
  quick; flag it if I am not.

Suggested branch names: `feat/api-skeleton`, `feat/alembic-migration`,
`feat/triage-providers`, `feat/state-machine`, `feat/redis-cache`,
`test/backend-suite`.

## 8. When you are blocked

- Collaborator access: done — you are `@ashar1x` with push access.
- Housekeeping: the persistence proof left a `persistence_probe` table in the dev
  Postgres (`docs/evidence/21-postgres-persistence.txt`). Drop it before your
  Alembic `0001` migration so your baseline is clean:
  `kubectl -n civicpulse exec statefulset/postgres -- psql -U civicpulse -d civicpulse -c 'DROP TABLE persistence_probe'`
- Contract is ambiguous or you need a field the contract does not have → open
  an issue and ping Ali **before** implementing, so the frontend typed client
  and the contract do not drift apart.
- Your change needs a new environment variable → say so in the PR; it has to go
  into the K8s ConfigMap (non-secret) or Secret (secret) plus `.env.example`,
  and the `k8s/` manifests are Ali's to review.

## 9. What I deliberately did not do

The stub in `tools/stub-backend/` implements the whole contract in memory. It is
scaffolding so the frontend, Compose, Kubernetes and CI could be built and
proven before your code existed — it is explicitly not production code and earns
none of the backend, data, cache or AI marks. Ali's AI agent started to write
the triage layer and then deleted it, because that is your issue #4. If you would
rather the stub were cut back to health + a bare 201 so there is no temptation to
port it, say so and Ali will trim it.
