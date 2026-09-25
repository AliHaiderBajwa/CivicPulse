# CivicPulse: 48-Hour Plan (Ashar + Ali Haider)

CS4032 Assignment 1. Two people, two days, one repo. This file is the step-by-step procedure. Tick the boxes as you go.

---

## 0. Read this first

### The honest picture
The PDF estimates 35-45 hours per student. You have about 24-28 focused hours each. So you cannot build everything at full polish. The plan below is built on four rules:

1. **Never trigger an automatic deduction.** They cost more than most features earn (section 10).
2. **Spend time by mark value.** The PDF itself says the order is AI layer (F) > Backend (C) > CI/CD (I) > Kubernetes (H).
3. **Skip the bonus** unless everything else is green. Only the zero-downtime demo is cheap enough to try.
4. **Submit on time.** Late submissions get nothing, and imperfect on time beats perfect late.

### What is thin or cut on purpose

| Item | Decision |
|---|---|
| All bonus items except (maybe) zero-downtime rollout | Cut. Try zero-downtime only in the last hours |
| Grafana, OpenTelemetry, Argo CD, Cosign | Cut |
| Gemini provider | Cut (Groq is enough) |
| OllamaTriage | Thin: a subclass of the LLM provider pointing at Ollama's OpenAI-compatible URL. Container and volume exist under a Compose profile. Not demoed live |
| Frontend polish | Functional only. Use AI for boilerplate (allowed, but disclose in `docs/AI-USAGE.md`) |
| VPA | Install, run one load test, commit the recommendation, update requests, write the explanation. No extra experiments |

### The spine: never skip these
- The **fallback test**: provider that always raises, `POST /api/complaints` returns 201 and `triaged_by == "rules:fallback"`.
- `needs:` on every publishing/deploying job. Deploy by SHA, never `:latest`.
- Pinned image tags, non-root users, exec-form `CMD`.
- Two Compose networks (`internal: true` on the data one).
- Postgres as a **StatefulSet with a PVC**. Redis with a PVC.
- Resource **requests** on every pod (the HPA is useless without them).
- No `.env`, key or token in git history. Ever.

### Time notation
`H0` = the moment you start Day 1. `D2-H0` = the start of Day 2. Shift everything to your real deadline. **The last 2 hours of Day 2 are a freeze: docs, evidence, video, submission. No new features.**

### Reality check (this machine, Ali's keyboard)
Audit against the original PDF found these deltas from the plan's assumptions. All are now binding:

- **Repo is `https://github.com/AliHaiderBajwa/CivicPulse.git`** (public, empty) — created by Ali, not `ashar1x/civicpulse`. Ashar gets added as collaborator.
- **RAM: 3.7 GB + 3.9 GB swap** (not 6–8 GB Docker RAM). k3d works only with the `firdousi-foods-courier` containers paused during the K8s block. Ollama stays profile-only, never demoed live.
- **Ports 5432 and 6379 are taken** by another project. Publish **no** database/cache ports in *any* compose file, dev included.
- **Tooling (kubectl, k3d, kustomize, kubeconform, k6, trivy, syft, matplotlib) is not installed** — pre-flight installs them before H0.
- **Image pins (G1):** `postgres:16-alpine`, `redis:7-alpine`, `nginx:1.30.5-alpine3.24`, `node:22-alpine`, `python:3.12-slim` — exact tags are contractual, unpinned = −8.
- **Seed spread (G5):** seed data must cover all 6 categories with varied priorities/statuses, not just 30 rows.
- **Rubric C says "ten endpoints", the §2.2 table lists nine.** Implement every table row exactly; keep `/openapi.json` exposed; ask the instructor about the count — do not guess.

---

## 1. Pre-flight (do before the clock starts, about 45 minutes)

Both of you.

### Windows setup
- [ ] Use **WSL2 (Ubuntu)** and keep the repo inside it (`~/civicpulse`), not under `/mnt/c`. Builds and file watching are much faster.
- [ ] Docker Desktop with WSL integration on. Give it **6-8 GB RAM**. Turn off Docker Desktop's built-in Kubernetes so it doesn't clash with k3d.
- [ ] Install Homebrew for Linux inside WSL (easiest way to get the tools below).

### Tools
```bash
# inside WSL
brew install gh kubectl k3d kustomize kubeconform helm k6 trivy syft
# Python 3.12 (apt or uv) and Node 22 (nvm install 22)
```

### Verify everything
```bash
docker --version && docker compose version
python3 --version        # 3.12.x
node -v                  # v22.x
git --version && gh --version
kubectl version --client
k3d version
kustomize version
kubeconform -v
k6 version
trivy --version
syft version
```

### Accounts and keys
- [ ] GitHub account each. `gh auth login` done.
- [ ] **Groq API key each** (console.groq.com). Rate limits are per organization, so don't share one key. Keys go in your local `.env` only.
- [ ] Ali is added as a collaborator on the repo.

### Who does what (summary)

| Ashar | Ali |
|---|---|
| Backend, database, Redis cache and rate limiter, AI layer, backend Dockerfile, backend tests | Frontend, Compose, Kubernetes, CI/CD, evidence for infra |
| **Spare-capacity jobs (Day 2):** ADRs 0001 + 0004, TRIAGE.md, k6 script + plotting script + HPA logger, README API table | **Also owns:** the 5+ frontend Vitest tests (he writes the components). Ali is the bottleneck, so protect his time |

---

## 2. Block 0: together (H0 to H1.5): the contracts

Do this on a call. Everything after it can run in parallel. **Freeze these; if one has to change, message the other first.**

### Step 1: create the repo (Ashar, 10 min)
```bash
# DONE (reality): Ali already created https://github.com/AliHaiderBajwa/CivicPulse.git — PUBLIC, empty.
git clone https://github.com/AliHaiderBajwa/CivicPulse.git && cd CivicPulse
git checkout -b dev && git push -u origin dev
```
The repo is public (branch protection on private repos needs a paid plan). Ali adds Ashar: Settings > Collaborators.

### Step 2: protect `main` (Ashar, 5 min)
Settings > Branches > Add rule for `main`:
- [x] Require a pull request before merging, **1 approval**
- [x] Require status checks (add them **after** the first CI run; GitHub only lists checks that have run)
- [x] Do not allow bypassing settings; block force pushes
- Screenshot the rule into `docs/evidence/01-branch-protection.png`.

The initial README commit is the only commit that goes straight to `main`. After that, nothing does.

### Step 3: create the Issues (Ashar, 10 min)
Every PR must link an Issue (`Closes #N` in the PR body). Create these now so you can just reference them:

| # | Issue | Owner |
|---|---|---|
| 1 | API skeleton + OpenAPI contract | Ashar |
| 2 | Repo scaffold, `.env.example`, stub backend | Ali |
| 3 | DB migration + idempotent seed | Ashar |
| 4 | Triage providers + fallback + validation | Ashar |
| 5 | Complaint API + state machine + request logging | Ashar |
| 6 | Redis stats cache + rate limiter | Ashar |
| 7 | Frontend: submit, dashboard, stats | Ali |
| 8 | Compose dev/prod, networks, volumes | Ali |
| 9 | CI workflow | Ali |
| 10 | Backend test suite | Ashar |
| 11 | Kubernetes manifests | Ali |
| 12 | CD + release workflows | Ali |
| 13 | Frontend tests | Ashar |
| 14 | Docs + ADRs | both |

### Step 4: freeze the contracts (both, 60 min)

Create these in the first PRs (Issue 1 and 2), and treat them as law.

**Names and ports**
- Compose service names: `frontend`, `backend`, `database`, `cache`, `ollama`. Kubernetes Services use the **same names**, so one nginx config works everywhere.
- Backend port **8000**. Frontend (nginx) port **8080** (non-root can't bind 80).
- Image names: `ghcr.io/alihaiderbajwa/civicpulse-backend` and `ghcr.io/alihaiderbajwa/civicpulse-frontend` (lowercase — GHCR requires it).

**`.env.example`** (Ali commits it; placeholders only)
```
POSTGRES_USER=civicpulse
POSTGRES_PASSWORD=change-me
POSTGRES_DB=civicpulse
DATABASE_URL=postgresql+psycopg://civicpulse:change-me@database:5432/civicpulse
REDIS_URL=redis://cache:6379/0
TRIAGE_PROVIDER=simulated        # llm | ollama | rules | simulated
LLM_API_KEY=
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
OLLAMA_URL=http://ollama:11434/v1
RATE_LIMIT_PER_MIN=10
LOG_LEVEL=INFO
IMAGE_TAG=latest
```
(Check Groq's current model list and use whatever small instruct model is available. Note what you saw in the notes.)

**Backend commands Ali can rely on**
- `alembic upgrade head` (migrations)
- `python -m app.seed` (seed)
- image CMD runs uvicorn on 8000

**Rules both follow**
- Migrations run from a one-off step (a Compose one-shot service, a Kubernetes initContainer or Job). **Never** in app startup code.
- Client IP for the rate limiter: Ali's nginx sets `X-Forwarded-For`; Ashar's limiter reads it first.
- Validation errors return **400** (not FastAPI's default 422) with a field-level body: `{"detail":[{"field":"text","message":"..."}]}`.
- The frontend has **no** list of status transitions. It offers all four statuses, the backend decides, and the UI shows the 409 message verbatim.

**The two things that unblock each other**
- **Ashar** pushes a FastAPI skeleton with all 9 routes, Pydantic models and stub bodies, and exports `docs/openapi.json`. Ali generates his typed client and mock server from it.
- **Ali** writes `tools/stub-backend/` (about 20 lines: `/health`, `/ready`, `/api/stats` with an `X-Cache` header) so Compose and Kubernetes can be built without the real backend.

**Done when:** `dev` contains the repo layout from the PDF (section 5.7), `.env.example`, `docs/openapi.json`, the stub backend. `.gitignore` includes `.env`.

---

## 3. Day 1

### Block 1 (H1.5 to H5): the core
**Ashar: data + API core**
- [ ] Alembic migration `0001`: all columns from the PDF's schema table, 4 enums, `timestamptz`, `gen_random_uuid()` default, DB-level `CHECK` constraints (text 10-2000, location 3-200, summary <= 140), both indexes (`(status, priority)` and `created_at`), working `downgrade()`.
- [ ] Repositories (all SQL lives here), services, routes. Get `POST`, `GET id`, `GET list` (filters, `page`, `page_size <= 100`, `total`) and `PATCH status` working.
- [ ] State machine as an explicit dict: `open -> {in_progress, rejected}`, `in_progress -> {resolved, rejected}`, terminals -> `{}`. Invalid transition returns 409 naming the transition.
- [ ] `RuleBasedTriage` + `SimulatedTriage` + factory + `TriageProvider` protocol. Use the LLM-free path so the API works end to end today.
- [ ] Idempotent seed: 30+ Urdu-influenced English complaints, deterministic `uuid5` IDs, `ON CONFLICT DO NOTHING`, `triaged_by='rules'`. **Spread across all 6 categories, all 3 priorities and all 4 statuses.** Run it twice and confirm the row count doesn't change.
- Dev shortcut: two plain containers for Postgres and Redis on your machine; you don't need Ali's Compose yet.

**Ali: frontend against the mock**
- [ ] Vite + React 18 + TypeScript. Mock: `npx @stoplight/prism-cli mock docs/openapi.json`.
- [ ] Typed client from `openapi-typescript`.
- [ ] Submit view: validation mirroring the server, loading state, shows category, priority, AI summary and provider.
- [ ] Dashboard: pagination, three filters, status control that shows the server's 409 message verbatim.
- [ ] `nginx.conf` proxying `/api` to the backend, upstream via env (nginx `templates/` + `envsubst`, default `backend:8000`), sets `X-Forwarded-For`. This is your runtime-config answer (ADR 0002).
- [ ] Frontend `Dockerfile`: `node:22-alpine` build, `nginx:1.30.5-alpine3.24` serve, listen on 8080, non-root (`USER nginx`, writable cache dir, pid under `/tmp`), `.dockerignore`.

**Checkpoint (H5):** Ashar's API answers on `localhost:8000` with seeded data. Ali's UI works against the mock. Open the PRs (Issues 1, 2, 3, 5, 7) and review each other's within 15 minutes.

### Block 2 (H5 to H8): the parts that earn the most marks
**Ashar: AI layer and Redis (the highest-value block)**
- [ ] `LLMTriage`: `openai` SDK with `base_url` pointed at Groq, JSON mode, **10 s timeout**, validate the reply with `TriageResult.model_validate_json`. Any failure (prose, code fence, out-of-enum category, long summary) counts as a provider error.
- [ ] **One retry with jitter**, only on timeout, 429 and 5xx. Never retry a 400.
- [ ] On failure: `RuleBasedTriage`, `triaged_by = "rules:fallback"`, one WARNING log with complaint id, provider, error class.
- [ ] Prompt-injection guardrail: complaint text delimited and labelled as data, output limited to the enum.
- [ ] `OllamaTriage` (thin): same class, `OLLAMA_URL` base.
- [ ] Content-hash cache in Redis (SHA-256, TTL 24 h). Write a small script that submits duplicates and prints the hit rate; keep the number for the notes.
- [ ] `/api/stats` read-through cache: TTL 30 s, `X-Cache: HIT|MISS`, **invalidated on create and on status change**.
- [ ] Rate limiter: Redis counter keyed by client IP on `POST /api/complaints`, 429 with `Retry-After`.
- [ ] `/health` (no DB), `/ready` (DB + Redis, 503 naming the failed one), `/metrics` (request count, latency histogram, triage latency, fallback counter), `/api/meta/providers` (active provider + last 20 outcomes).
- [ ] JSON logging to stdout with `request_id` (from `X-Request-ID`, generated if absent). SIGTERM closes the DB pool and Redis cleanly.

**Ali: Compose**
- [ ] `compose.yaml` (dev, `build:`) and `compose.prod.yaml` (`image: ghcr.io/alihaiderbajwa/...:${IMAGE_TAG}`, **no `build:` anywhere**, no published DB or cache ports — **and none in dev either: 5432/6379 are already taken on this machine**).
- [ ] Networks: `edge` (bridge) and `internal` (bridge, `internal: true`). Frontend on `edge` only; backend on both; database and cache on `internal` only.
- [ ] `ollama` service on `edge` (it must download its model, which an internal network cannot do), under a Compose **profile** so normal runs and CI don't pull it.
- [ ] Volumes: `pgdata`, `redisdata` (Redis with `--appendonly yes`), `ollama_models`. Dev-only bind mount on the backend for hot reload. **Required (G2): put the justification sentence in the files themselves** — a comment in `compose.yaml` saying why hot-reload source mounting is right for dev, and a comment in `compose.prod.yaml` saying why shipping source into a deploy image is wrong.
- [ ] Healthchecks on **every** service (`pg_isready`, `redis-cli ping`, HTTP for backend/frontend, `ollama list`), `depends_on: condition: service_healthy`, pinned tags, `restart: unless-stopped`, `deploy.resources` limits, credentials via `${...}`.
- [ ] Run everything against the stub backend. Prove `docker compose exec frontend ping database` fails, and screenshot it.
- [ ] Stats view + error boundary in the frontend.
- [ ] **5+ meaningful Vitest tests** (form validation, loading state, provider shown, 409 message rendered verbatim, X-Cache badge). Get `eslint` and `tsc --noEmit` clean.

**Checkpoint (H8):** Ashar's AI + cache work locally. Ali's Compose stack runs with the stub. PRs for Issues 4, 6, 8 open and reviewed.

### Block 3 (H8 to H10): tests, backend image, first CI
**Ashar**
- [ ] `backend/Dockerfile`: `python:3.12-slim` pinned, builder stage, requirements copied **before** source, non-root user, exec-form CMD, `HEALTHCHECK` using Python `urllib` (the slim image has no `curl`), `.dockerignore`. Record the build-context size before and after.
- [ ] Tests (need **14+**, coverage >= 65%, deterministic, no `time.sleep`):
  1. **Must-have:** always-raise provider still returns 201 with `rules:fallback`.
  2. Malformed-JSON provider is rejected by the validator and falls back.
  3. Prompt-injection test: category still comes from the schema.
  4. State machine: every valid and invalid transition (parametrized).
  5. Validation errors return 400 with field-level bodies.
  6. Rate limiter returns 429 with `Retry-After`.
  7. Stats cache MISS then HIT, and invalidated after a write.
  8. `/health` works with the DB down; `/ready` returns 503 naming the dependency.
  9. Seed is idempotent.
  10. Pagination limit (`page_size` 101 is rejected).
- [ ] Run `ruff` and `mypy` clean.

**Ali: `ci.yml`**
- Triggers: pull request to `main`, push to `dev`.
- Jobs: `lint-and-type`, `test-backend` (Postgres + Redis service containers, `TRIAGE_PROVIDER=simulated`, coverage gate 65%), `test-frontend`, `build` (no push), `scan` (Trivy, `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`), `manifests` (`kustomize build k8s/overlays/prod | kubeconform -strict -summary -`), `integration`.
- `integration`: copy `.env.example` to `.env`, `docker compose up -d --wait`, wait for `/ready`, POST a complaint, GET it back, assert the category, check `X-Cache` goes MISS then HIT, `docker compose down -v`.
- Add a top-level `permissions: contents: read` block; pin actions to `@v4` or newer version tags.

### Block 4 (H10 to H12): integration day
- [ ] **Swap the stub for the real backend.** `docker compose up --build`. Fix contract mismatches together. This is where most surprises appear.
- [ ] **Deliberate merge conflict** (Part A, 3 marks). Both edit the `HEALTHCHECK` line in `backend/Dockerfile` from separate branches:
  ```bash
  # Ashar
  git checkout -b feat/healthcheck-interval dev
  # edit HEALTHCHECK (interval/timeout) -> commit -> push -> merge PR into dev first
  # Ali
  git checkout -b feat/healthcheck-endpoint dev
  # edit the SAME line (point it at the endpoint compose expects) -> commit -> push
  git fetch origin && git merge origin/dev     # conflict appears
  # screenshot the <<<<<<< markers, resolve, then:
  git add backend/Dockerfile && git commit
  git log --graph --oneline -n 10              # screenshot the merge
  ```
  Save screenshots as `docs/evidence/02-conflict-markers.png`, `03-conflict-resolved.png`, `04-merge-graph.png`, and write 2-4 sentences on why that version won.
- [ ] Merge everything into `dev`. Add the CI job names as required checks on `main` and re-screenshot the rule.
- [ ] Ali starts `k8s/base/` (namespace, postgres StatefulSet, redis). Ashar reviews PRs and fixes whatever integration exposed.

**End-of-Day-1 target:** `docker compose up` on a fresh clone brings up the whole system with seeded data. CI is green on `dev`. If you can also do a first `dev` to `main` PR tonight, do it; it surfaces CD problems while you still have a full day to fix them.

---

## 4. Day 2

### Block 5 (D2-H0 to D2-H3)
**Ali: Kubernetes to completion**
- [ ] Kustomize: `k8s/base/` + `overlays/dev` + `overlays/prod`. Everything in namespace `civicpulse`.
- [ ] Backend and frontend Deployments, 2+ replicas each. Postgres **StatefulSet** with `volumeClaimTemplates`. Redis Deployment + PVC (AOF on). Four **ClusterIP** Services named `backend`, `frontend`, `database`, `cache`. Ingress: `/` to frontend, `/api` to backend, one host (e.g. `civicpulse.localhost`).
- [ ] ConfigMap for non-secrets. `secret.yaml` with **placeholders only**. Real values come from `kubectl create secret` in CI or by hand locally, never committed (not even base64: -15).
- [ ] Probes: `startupProbe` and `livenessProbe` on `/health`, `readinessProbe` on `/ready`. Numbers exactly as in the PDF (`failureThreshold: 30`, `periodSeconds: 2`).
- [ ] Rolling update: `maxSurge: 1`, `maxUnavailable: 0`, `terminationGracePeriodSeconds`, `preStop` sleep.
- [ ] `resources.requests` **and** `limits` on every container (use a small CPU request like `100m` so the HPA reacts to a modest load).
- [ ] HPA v2 (min 2, max 10, CPU 60%, scale-down window 300 s, scale-up 0 s), PDB (`minAvailable: 1`), VPA with `updateMode: "Off"`.
- [ ] Create the cluster, install metrics-server (k3d ships one; kind needs `--kubelet-insecure-tls`), install VPA, deploy, hit the Ingress.
- [ ] **Persistence proof:** `kubectl delete pod postgres-0 -n civicpulse`, then show the rows are still there.

**Ashar: spare-capacity work (independent of the cluster)**
- [ ] `load/k6-script.js`: ramping load against `GET /api/complaints`, `GET /api/stats` and `POST /api/complaints` (with `TRIAGE_PROVIDER=simulated` so CPU load comes from the app, not the LLM).
- [ ] `scripts/plot_hpa.py`: reads a CSV of `timestamp,replicas,vus` and plots replicas against offered load with matplotlib.
- [ ] `scripts/hpa_logger.sh` (logs replica counts to CSV during the load test) and a local dry run of the k6 script against your own container. If you finish early, offer to take some of Ali's frontend tests.

### Block 6 (D2-H3 to D2-H6): CD and evidence gate
**Ali: `cd.yml` and `release.yml`**
- `cd.yml` on push to `main`: `test` -> `build-push` (needs `test`) -> `deploy-k8s` (needs `build-push`).
  - `build-push`: login to GHCR with `GITHUB_TOKEN` (`permissions: packages: write`), push both images tagged `${{ github.sha }}` and `latest`, Syft SBOM, image digest as a job output.
  - `deploy-k8s`: create a kind cluster in the runner, install ingress + metrics-server, `kubectl create secret` from GitHub Secrets (store `LLM_API_KEY` and the DB password as GitHub Secrets and build the Kubernetes Secret from them; the smoke test can still run with `TRIAGE_PROVIDER=simulated`), apply the prod overlay with `kustomize edit set image ...:${{ github.sha }}`, `kubectl rollout status`, smoke-test the Ingress, `kubectl get hpa`.
  - **Never deploy `:latest`.** Least-privilege `permissions:` on every workflow.
- `release.yml` on tag `v*`: semver tags + generated release notes.
- Expect several failed runs on the kind deploy. Budget time for that; it is the slowest feedback loop in the whole assignment.

**Ashar: docs that don't need Ali**
- [ ] `docs/adr/0001-provider-interface.md`
- [ ] `docs/adr/0004-pii-and-data-governance.md`: never send `reporter_contact`; redact phone, email and CNIC patterns from the text before sending; say what still leaves your machine, to whom, and why that's acceptable. Read Groq's current data terms and cite what you saw.
- [ ] `docs/TRIAGE.md` (how triage works, fallback chain, latency, measured cache hit rate)
- [ ] The "triage is failing" section of `docs/RUNBOOK.md`
- [ ] README API table and problem statement

### Block 7 (D2-H6 to D2-H8): load test, VPA, gate evidence
- [ ] **HPA test (together).** Ali runs `kubectl get hpa -w -n civicpulse | tee docs/evidence/hpa-watch.txt` plus a loop logging `date,replicas` to CSV; Ashar runs k6. Then `python scripts/plot_hpa.py` produces the chart. Note the seconds between "load rises" and "replicas rise" (needed for the notes).
- [ ] **VPA loop:** record your guessed requests; run the load; `kubectl describe vpa backend-vpa -n civicpulse > docs/evidence/vpa-recommendation.txt`; update the requests to match Target; re-run and note what changed in HPA behaviour.
- [ ] **Red then green pipeline:** on `dev`, push a deliberately failing test; open the `dev` -> `main` PR; screenshot the red check and the blocked merge button (`05-red-check.png`, `06-blocked-merge.png`); push the fix; screenshot the green check (`07-green-check.png`); Ashar approves; merge. This merge is also the `cd.yml` run you submit.
- [ ] **Rollback, on video-ready terminals:** `kubectl rollout undo deployment/backend -n civicpulse`, then re-apply the previous overlay with the previous SHA. **Then write the required explanation into `docs/RUNBOOK.md` (G4): imperative undo = the 3 a.m. fast answer, declarative re-apply = the auditable correct answer once the fire is out — and when to use each.**
- [ ] **Stretch (only if green):** zero-downtime rollout. Run k6 while doing `kubectl set image`, show zero failed requests (+4).

### Block 8 (D2-H8 to D2-H10): documents
See the checklist in section 8. Split: Ashar writes Q4, Q8 (his), the index explanations, the Redis AOF answer and the measured cache hit rate; Ali writes Q1, Q2, Q3, Q5, Q6, Q7. Every answer needs **file-and-line references**; generic answers score zero.

### Block 9 (D2-H10 to D2-H12): freeze
- [ ] Record the video (section 9).
- [ ] Run the submission checklist (section 10).
- [ ] Viva swap (section 12).

---

## 5. Git rules that keep Part A safe (15 marks)

- Feature branch, then PR into `dev`, partner reviews, merge. `dev` to `main` only by PR with one approval. **No direct pushes to `main`** (-5).
- Branch names: `feat/...`, `fix/...`, `docs/...`, `ci/...`.
- Commit prefixes: `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`.
- Commit small. You need **35+ commits total, neither of you under 35%** (`git shortlog -sn`). One commit per finished checkbox works.
- Each PR: `Closes #N`, a description, and a **substantive** review comment from the other person (say what you checked, not just "LGTM").
- **15-minute rule:** when your partner pings a PR, review it within 15 minutes. This is the difference between a plan that works in two days and one that stalls.
- Note: `ci.yml` runs on PRs to `main` and pushes to `dev`, so feature PRs into `dev` won't show checks. That's expected. CI runs when they land on `dev`.

**Never commit:** `.env`, keys, tokens, real Kubernetes secrets. If you do, it costs -20 and you must rotate the credential and write an incident note.

---

## 6. Evidence checklist (`docs/evidence/`)

- [ ] `01-branch-protection.png`
- [ ] `02-conflict-markers.png`, `03-conflict-resolved.png`, `04-merge-graph.png`
- [ ] `05-red-check.png`, `06-blocked-merge.png`, `07-green-check.png`
- [ ] `08-ping-fails.png` (frontend cannot ping database)
- [ ] `hpa-watch.txt` and `hpa-replicas-vs-load.png`
- [ ] `vpa-recommendation.txt`
- [ ] Build-context sizes before/after (both images) and both image sizes
- [ ] `git shortlog -sn` output
- [ ] Persistence proofs: `docker compose down/up` and Postgres pod deletion, rows still present
- [ ] Measured triage cache hit rate

---

## 7. Docs checklist (Part J, 15 marks)

| File | Owner | Minimum content |
|---|---|---|
| `README.md` | Ali skeleton, Ashar API table | Problem statement, badges, Mermaid architecture, one-command quickstart, API table, screenshots. **Test the quickstart on a fresh clone** |
| `docs/adr/0001-provider-interface.md` | Ashar | Why a `TriageProvider` protocol, alternatives, consequences |
| `docs/adr/0002-frontend-runtime-config.md` | Ali | nginx-proxied `/api` and `envsubst`, why not baked-in `VITE_` values |
| `docs/adr/0003-deploy-by-sha.md` | Ali | Why deploy by commit SHA and never `:latest` |
| `docs/adr/0004-pii-and-data-governance.md` | Ashar | What leaves your machine, to whom, and why it's acceptable |
| `docs/RUNBOOK.md` | Ali (deploy, rollback, logs), Ashar (triage failing) | Commands, not prose |
| `docs/TRIAGE.md` | Ashar | Fallback chain, latency, cache hit rate |
| `docs/AI-USAGE.md` | Both | **(G6) Disclosure must be honest and specific: this project is built with an AI coding agent (opencode) pair-programming at Ali's keyboard and Ashar's.** Name the tools, which files/features the agent wrote or shaped, what each partner changed afterwards and why, and what you verified yourself. "AI for boilerplate" understates it — understating risks plagiarism territory; specific disclosure carries no penalty, but you must be able to defend every line in the viva. |
| `docs/ENGINEERING-NOTES.md` | Both | The 8 questions below |
| `scripts/check_submission.py` | Ali | Use the instructor's if provided; otherwise a small script that greps for `.env`, keys, `:latest`, `localhost` |

### The 8 engineering questions
1. Three laptop-vs-CI differences and the exact Dockerfile/manifest lines that freeze them (Ali).
2. Position on the CI/CD maturity ladder (Lecture 03, slide 32), the next rung and what it buys (Ali).
3. The exact line that guarantees build-once-deploy-many, and what breaks without it (Ali).
4. What "correct" means for a probabilistic LLM component and how CI stayed deterministic (Ashar).
5. HPA lag in seconds, where the time went, what would reduce it (Ali).
6. Why VPA runs in Off mode, and the failure mode of Auto alongside HPA (Ali).
7. Where the `internal: true` network leaves the LLM-calling service, and how you resolved it. Answer: the backend bridges both networks and `edge` has outbound access, so the LLM call lives there (Ali writes, Ashar confirms).
8. The failure that cost more than an hour: symptoms, what you wrongly believed, the command or log line that revealed the truth (each of you writes your own, keep the best one or both).

Also required in the notes, and easy to forget: the reason for each index (name the query), **all three volume justifications — `pgdata`, `redisdata` (AOF) and `ollama_models`, each with its own sentence** (rubric G says "each justified", not just the AOF one), Groq's live rate limits as you saw them, the build-context numbers, and the measured cache hit rate.

---

## 8. Video script (max 5 minutes, both speak)

| Time | Who | Show |
|---|---|---|
| 0:00-0:40 | Ali | Clean clone, one command, system up with seeded data |
| 0:40-1:30 | Ashar | Submit a complaint, show category/priority/summary/provider; submit a duplicate (cache) |
| 1:30-2:10 | Ashar | Force the fallback (bad key or fail injection): still 201, `rules:fallback`; show `/api/meta/providers` |
| 2:10-2:30 | Ashar | Hit the rate limit: 429 with `Retry-After` |
| 2:30-3:00 | Ali | `docker compose exec frontend ping database` failing |
| 3:00-4:00 | Ali | HPA scaling under k6 load |
| 4:00-4:40 | Ali | `kubectl rollout undo`, then the declarative rollback |
| 4:40-5:00 | Both | Wrap-up |

Record it in two takes; each of you records your own part and splice, or do one shared call recording. Upload as **unlisted**.

---

## 9. Final submission checklist (section 5.8 of the PDF)

Run in the repo root before submitting:
```bash
python scripts/check_submission.py
git log --all --full-history --oneline -- .env      # must print nothing
git grep -nE "(api[_-]?key|secret|password)\s*[:=]" -- ':!*.example' ':!docs'
git grep -n ":latest" -- k8s compose.prod.yaml .github  # never deployed
git shortlog -sn
```

- [ ] GitHub repo URL (public, or both instructors added)
- [ ] Link to a **successful** `cd.yml` run that tested, published and deployed
- [ ] Links to both GHCR images showing SHA tags
- [ ] Demo video link (unlisted)
- [ ] `git shortlog -sn` output pasted
- [ ] `kubectl get hpa -w` capture and the replicas-vs-load chart

---

## 10. Automatic deductions: last scan

- [ ] No `.env`, key, token or password in git history (-20)
- [ ] No API key in a Kubernetes manifest, even base64 (-15)
- [ ] Every base image pinned; `postgres`, `redis`, `node` have tags (-8)
- [ ] No `localhost` for service-to-service calls (-8)
- [ ] Frontend cannot reach the database (-8)
- [ ] No published DB/cache port in `compose.prod.yaml`; no NodePort/LoadBalancer on the database (-8)
- [ ] Every publishing/deploying job has `needs:` (-8)
- [ ] Nothing deploys `:latest` (-8)
- [ ] Postgres is a StatefulSet with a PVC (-8)
- [ ] No direct commits to `main` (-5)
- [ ] README quickstart works from a fresh clone (-5)

---

## 11. If you fall behind: drop in this order

Cut from the bottom up. Never cut the spine (section 0).

1. Zero-downtime demo (stretch)
2. VPA experiments beyond one recommendation
3. Ollama container demo (keep the class and the profile)
4. Frontend styling
5. Second and third engineering-note paragraphs (answer all 8, but briefly, with file-and-line refs)

The PDF's own advice: value order is **F > C > I > H**. If Kubernetes is the thing behind schedule, keep the manifests and the probes, and shorten the HPA/VPA experiment to one clean run.

---

## 12. Viva prep (the multiplier: your mark is team mark x viva factor)

Each of you gets 10 minutes, individually, with the repo open, on **all** of the code. Block 60-90 minutes for a swap at the end of Day 2:
- Ashar explains the Kubernetes probes, the Compose networks, the CI jobs and the HPA/VPA conflict to Ali, and Ali explains the triage pipeline, state machine and rate limiter to Ashar.
- Each person practises being asked to **modify something live** (e.g. add a status transition, change the rate limit, change an HPA target).

Questions you should be able to answer cold:
1. Why is Postgres a StatefulSet and not a Deployment?
2. Why are `/health` and `/ready` separate, and what happens if you wire them backwards?
3. Why do both a 30 s TTL and explicit invalidation exist on `/api/stats`?
4. Why must the rate limiter live in Redis and not in a Python dict?
5. What happens if the LLM returns a category that isn't in the enum? What if it times out? What if it returns 400?
6. Why does the HPA need `resources.requests.cpu`?
7. Why is VPA in Off mode?
8. What line makes the frontend image environment-independent?
9. Why can't the frontend reach the database, and how did you prove it?
10. What does `git show <sha>` tell you about what production runs?

---

## 13. Process discipline (G7 — non-negotiable, runs itself)

Three artifacts are maintained **continuously, not at the end**. The rule lives in `AGENTS.md` so no work session (human or AI) can forget it:

1. **`PROGRESS.md`** — after *every* milestone: what was expected, what was achieved, evidence path, what's next. One entry per completed checkbox batch.
2. **`docs/CivicPulse-Documentation.docx`** — regenerated from the markdown sources after every milestone via `scripts/build_docx.py` (python-docx). Never hand-edited.
3. **`docs/RUBRIC-CHECKLIST.md`** — one checkbox per rubric line item (A1…J5 + bonus), ticked as evidence lands.

**Definition of Done for any milestone = code committed + PROGRESS.md entry + docx regenerated + rubric box ticked.** A milestone without all four is not done.

Reference material kept in-repo for both partners: `docs/ASSIGNMENT-BRIEF.md` (PDF requirements digest) and the original PDF itself.
