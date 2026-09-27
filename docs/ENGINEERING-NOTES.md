# ENGINEERING-NOTES — the eight questions (§5.2), with file-and-line refs

Split per the plan of record (`docs/PLAN.md` §7): Ashar owns the AI-layer,
backend and data answers; Ali owns the frontend runtime config, CI/CD and
Kubernetes answers. Refs point at the tree after PRs #25/#26 have merged.

---

### 1. Three laptop-vs-CI differences and the exact Dockerfile/manifest lines that freeze them — *Ali*

Three places where the laptop and CI deliberately differ, each frozen by a pinned line:

1. **Service addressing and published ports.** Compose talks over Docker DNS
   (`BACKEND_URL: backend:8000`, `compose.yaml:17`; `DATABASE_URL`/`REDIS_URL`
   env, `compose.yaml:40-41`, resolving against the `database`/`cache` hosts)
   and publishes host ports (8080 for the frontend, 8000 for the backend,
   dev-only — `compose.yaml:51`, never in `compose.prod.yaml`). CI instead
   maps the service containers to localhost
   (`postgresql+psycopg://…:…@localhost:5432/civicpulse`, `ci.yml:75`;
   `redis://localhost:6379/0`, `ci.yml:76`) and publishes nothing else.
   Both sides pin the identical images, so the bytes are equal and only the
   topology differs (`postgres:16-alpine`, `compose.yaml:76` and `ci.yml:53`;
   `redis:7-alpine`, `compose.yaml:100` and `ci.yml:66`).
2. **Persistence.** The laptop keeps named volumes across runs (`pgdata`,
   `redisdata` with AOF) — data survives `down`. CI starts empty on every
   run (fresh service containers; the integration job traps
   `docker compose down -v`). Same images, different lifecycle: this is why
   migrate-from-zero and seed idempotence are proven in CI rather than
   trusted from a long-lived laptop database.
3. **Dependency installation.** The laptop uses a venv / editable install;
   CI installs from the pinned `requirements.txt` fallback in `test-backend`,
   and images build from the hash-locked `requirements.lock`
   (`backend/Dockerfile`, `evidence/26` §1); the frontend `npm ci`s from its
   lockfile into a non-root nginx image (`frontend/Dockerfile:40-41`). No
   floating resolver step anywhere in the pipeline.

### 2. Position on the CI/CD maturity ladder (Lecture 03, slide 32), next rung and what it buys — *Ali*

On the standard ladder (manual → CI → continuous delivery to staging →
continuous deployment to production → progressive/self-service delivery), this
repo sits at **continuous delivery to a production-like ephemeral
environment**: every PR gets build, typecheck, tests, security scan and
contract validation; every merge to `dev` deploys SHA-pinned, SBOM'd images
to a fresh kind cluster with Ingress smoke. What it is *not* yet is
continuous deployment *to production*: there is no long-lived staging, no
human promotion step, and no progressive rollout.

The next rung is a persistent staging environment with promotion by the same
SHA-rewrite mechanism plus progressive delivery (canary or blue-green) and
GitOps reconciliation. What that buys: prod-parity confidence the ephemeral
cluster cannot give (real DNS/TLS, real data volumes, real traffic shape),
an auditable promotion trail, and safe incremental exposure instead of
all-at-once cutover.

### 3. The exact line that guarantees build-once-deploy-many, and what breaks without it — *Ali*

`.github/workflows/cd.yml:293`:
`sed -i -E "s|newTag: .*|newTag: ${SHA}|"` on the selected overlay.
That one line is the entire promotion mechanism: images are built exactly
once per commit, published under both the SHA and a `latest` alias
(`cd.yml:168,178` — verified same-digest in `evidence/22`), and the
environment is pointed at the tested bytes by rewriting the tag, never by
rebuilding. A pre-apply assertion then refuses any manifest containing
`:latest` and requires every owned image to end in `:${SHA}`
(`cd.yml:296-303`) — the −8 deduction is caught by code, not discipline.

Without it, the failure modes are: per-environment rebuilds (the running
bytes were never the tested bytes), `latest` ambiguity (two deploys minutes
apart running different code under one tag), and untraceable rollbacks.
With it, rollback is re-applying the previous SHA (`docs/RUNBOOK.md` §2)
and every running image traces to its commit, CI run and SBOM.

### 4. What "correct" means for a probabilistic LLM component, and how CI stayed deterministic — *Ashar*

**"Correct" is defined at the boundary, not inside the model.** The model is
probabilistic; nothing probabilistic is allowed to reach a client or a row
without passing four deterministic gates:

1. **Closed sets.** `category`/`priority` are enums
   (`backend/app/domain.py:4,13`) and `TriageResult` binds them with Pydantic
   (`backend/app/providers/triage/base.py:8-12`). The model is *asked* for
   these keys (`llm.py:12-23`) and *checked* against them
   (`llm.py:32-37`): an out-of-enum sample, a prose answer, a code fence or a
   >140-char summary is a `ProviderError`, i.e. a fallback — never a
   silently-wrong row.
2. **The fallback absorbs all residual risk.** `except Exception` at
   `triage_orchestrator.py:67` converts every provider failure into
   `RuleBasedTriage` with `triaged_by="rules:fallback"` (`:69`) and a WARNING
   (`complaint_service.py:30-35`). "Correct" therefore includes the degraded
   mode: still a valid enum, still a valid priority, still 201 — proven by
   `backend/tests/test_fallback.py:7-14`.
3. **Hostile input cannot flip the answer.** The complaint is wrapped and
   tag-stripped before it reaches the prompt (`llm.py:26-29`), the system
   prompt marks it untrusted (`llm.py:14-15`), and anything an obedient
   attacker-model outputs still has to clear gate 1
   (`backend/tests/test_injection.py`).
4. **Nothing probabilistic is cached unless it validated.** Only successful
   primary results are written (`triage_orchestrator.py:63-66`), and the
   cache re-validates on read (`:49`).

**How CI stayed deterministic:**

- The suite runs with `TRIAGE_PROVIDER: simulated`
  (`.github/workflows/ci.yml:77`) — a rules engine with fixed 0.99
  confidence (`simulated.py:23`) — and never touches the network; provider
  doubles live in `backend/tests/doubles.py`.
- Jitter is injectable: `LLMTriage(..., sleep=...)` defaults to `time.sleep`
  in production (`llm.py:51,56`) and is replaced by `lambda s: None` in
  tests, so retry tests exercise the logic without wall-clock waits
  (`test_llm_provider.py:60,66,80`).
- Assertions are on counters, headers and status codes — never on timing:
  cache proof is `X-Cache: MISS→HIT` plus `triage_cache_total` deltas
  (`evidence/25` §2, `evidence/28` [1]), rate-limit proof is status codes
  (`test_ratelimit.py`), fallback proof is a field comparison
  (`test_fallback.py:12`).
- The content-hash key is `sha256` over a normalised string
  (`triage_orchestrator.py:26-28`), so identical inputs give identical keys
  across machines; the fakeredis/real-Redis swap in `conftest.py` keeps the
  same semantics either way (verified against CI's exact install sequence,
  `evidence/27`).
- The real model call, when used, is `temperature=0`
  (`llm.py:65`) — the closest thing to determinism an LLM offers; the tests
  do not depend on it.

### 5. HPA lag in seconds, where the time went, what would reduce it — *Ali*

Measured from `docs/evidence/16-hpa-collect.csv` (166 samples) against
`docs/evidence/17-k6-rps.csv`, charted in `evidence/18`:

- Load ramps past 20 rps at **22:26:50** (peak 521.6 rps).
- First scale event **22:28:01**: 2 → 6 replicas at 213% CPU — **71 s lag**.
- 9 replicas at 22:28:13, all 10 by 22:28:19 (**+89 s**).
- Load ends 22:30:30 (2.4 rps); back to 2 replicas at 22:32:17 (**+107 s**).
- One flapping blip: 3 replicas at 22:35:10 (CPU 71%), reabsorbed to 2 by
  22:40:40 — the stabilization window doing its job visibly.

Policy (`k8s/base/hpa.yaml`): min 2 / max 10 (`:15-16`), CPU target 60%
(`:21`), scale-up stabilization **0 s** (`:28`), scale-down 300 s (`:26`).
Where the 71 s went: the metrics pipeline dominates (metrics-server scrape
cadence plus HPA sync — on the order of a minute), with pod startup and
readiness gates making up the remainder. Scale-up stabilization is 0 *by
design* (users are waiting), so no policy delay hides in the upward path;
the downward path is deliberately slow (300 s window) because flapping
replicas is more expensive than idle ones.

What would reduce the lag: a shorter metrics-server resolution, a
leaner/faster-ready image, or warm standby pods — each trading cost or
complexity for seconds. The honest attribution is that well over half the
observed lag is pipeline delay, not application startup.

### 6. Why VPA runs in Off mode, and the failure mode of Auto alongside HPA — *Ali*

The VPA runs recommender-only (`updateMode: "Off"`,
`k8s/base/vpa.yaml:19`); its current recommendation is committed in
`evidence/13` and applied to requests by a human, not by the machine. Auto
mode alongside this HPA would fight it, as the comment at the top of the
file states (`vpa.yaml:1-4`): the VPA raises the CPU request, computed
utilisation drops, the HPA scales in, per-pod load rises, the VPA raises the
request again — an oscillation loop. Recommender + HPA is the stable pairing:
one system decides *how many* pods, the other *advises* how big; the human
closes the loop on a schedule instead of every sync interval.

### 7. Where the `internal: true` network leaves the LLM-calling service, and how you resolved it — *Ali writes, Ashar confirms*

**K8s side — *Ali*.** The honest headline first: the cluster has **no
NetworkPolicies** (verified by grep — flat pod network), so K8s does *not*
replicate Compose's `internal: true` isolation. What it has instead:
ClusterIP-only services (`k8s/base/services.yaml:12,29,46,63`), no published
DB/cache ports anywhere (no NodePort/LoadBalancer; external traffic enters
only through the Ingress), credentials exclusively via `secretKeyRef`
(`k8s/base/backend.yaml:32-44`, never env literals), and DNS-only service
discovery (no `localhost`). The LLM call egresses through the node's default
route with no egress control — acceptable here because there are no hostile
in-cluster actors, secrets never land in images, and Postgres/Redis are
unreachable from outside the cluster. What would close it: a default-deny
NetworkPolicy with explicit allow rules (backend→database/cache/DNS,
Ingress→frontend/backend, backend→internet for the LLM).

*Ashar's confirmation of the Compose side (agreed — matches the file):*

- `backend` joins **both** networks — `edge` and `internal`
  (`compose.yaml:54-56`) — so it is the only service that can both reach the
  database/cache and egress to the internet.
- `frontend` joins **only** `edge` (`compose.yaml:18-19`): with
  `internal: true` on the database/cache network (`compose.yaml:145-146`) the
  browser-facing container has no route to Postgres or Redis at all.
- The egress the LLM call needs traverses `edge`, which is a plain bridge
  with a route out (`compose.yaml:142-143`), and service-to-service calls use
  Compose DNS (`BACKEND_URL: backend:8000`, `compose.yaml:17`) — no
  `localhost` anywhere in the path.

### 8. The failure that cost more than an hour: symptoms, wrong belief, the line that revealed the truth — *Ashar*

**The email regex that was "obviously fine".**

- **Symptoms.** Sonar raised `python:S8786` on
  `backend/app/services/redaction.py:9`: *"super-linear performance due to
  backtracking."* The gate stayed red. Separately, feeding `redact()` a
  50 000-character hostile body (dots and `@` arranged to maximise
  backtracking) took **~42 seconds** inside a single request — a trivially
  reachable worker stall on a public endpoint.
- **What I wrongly believed.** Two beliefs, both wrong. (a) *"The tests pass
  in milliseconds, so the pattern is fast enough"* — the fixtures were
  short, well-formed strings; they could never exercise the nested-quantifier
  path that blows up. (b) *"The outer group is bounded `{1,5}`, so the whole
  thing is bounded"* — the cost lives inside the nested `+` runs, and bounding
  the outer repetition bounds nothing about the backtracking between
  overlapping `[\w-]+` runs and the literal dots. When I finally switched to
  possessive quantifiers (`[\w.+-]++@[\w-]++(?:\.[\w-]+){1,5}+`,
  `redaction.py:9`), Python 3.11+ forbids backtracking into matched runs and
  the same hostile input dropped to **8.6 ms** — and Sonar *still* flagged it,
  because its parser does not model possessive quantifiers, which started a
  second hour-ish detour through suppression syntax (`# NOSONAR: …` invalid,
  `# NOSONAR(python:S1172)` rejected by the Python analyzer as `S7632`, bare
  `# NOSONAR` finally correct).
- **What revealed the truth.** Measuring the adversarial input directly
  instead of trusting happy-path tests — one script, one 50k-char string, a
  stopwatch: 42 000 ms vs 8.6 ms. The benchmark now lives *inside* the code
  comment at `redaction.py:3-8` so the suppression defends itself, and the
  full transcript is in `docs/evidence/25-complaints-api.txt` (S8786 entry in
  PR #25's review thread).
- **Lesson (kept).** Validators and sanitizers are adversarial surfaces: test
  them with hostile inputs and static analysers, not with fixtures. This is
  why `backend/tests/test_redaction.py` exists and why the F4 probe script
  exits non-zero on anomalies rather than printing a number unconditionally.

---

## Also required in these notes

### Reason for each index (named query) — *Ashar*

| Index | Query it serves | Why it needs to exist |
|---|---|---|
| `ix_complaints_created_at` (btree on `created_at`) | `ComplaintRepository.list()` orders every page by `created_at DESC, id` (`backend/app/repositories/complaint_repository.py:42`) — the `GET /complaints` feed the frontend renders first | Without it, every page-1 request sorts the whole table. The index delivers rows already in feed order. |
| `ix_complaints_status_priority` (btree on `(status, priority)`) | The same `list()` with filters: equality predicates on `status` and `priority` are applied at `complaint_repository.py:35-39` — the dashboard's "open + high" queue | Composite order matches the predicate shape (both columns equality-bound), so one index serves the queue scan; a single-column index would still need a second lookup per row. |

Schema, checks and both indexes: `evidence/23` (`psql \d complaints`).

### Why the stats cache has both a TTL and write-invalidation — *Ashar*

They defend against different staleness sources, so neither alone is enough:

- **Invalidation covers the writes we can see.** Every mutation of the data
  goes through `ComplaintService` — create (`complaint_service.py:29`) and
  status change (`complaint_service.py:54`) both call
  `StatsService.invalidate()`, which deletes the Redis key
  (`stats_service.py:23-24`). After any of our own writes the very next read
  is a MISS → recompute, so the dashboard is never stale behind our own
  mutations — proven by the MISS-immediately-after-POST step in
  `evidence/25` §2, well inside the 30 s window.
- **TTL covers the writes nobody can see.** Invalidations are only as good as
  every call site: a missed one, a background job, a second replica after a
  scale-out, or Redis losing the key (restart/eviction) would otherwise mean
  *permanent* staleness. The 30 s TTL (`config.py:23`, applied at
  `stats_service.py:20`) bounds the worst case to 30 seconds regardless of
  the cause — the safety net under the invariant.
- **Read-through + `X-Cache: HIT|MISS`** (`stats_service.py:16-21`) makes the
  cache's behaviour externally observable, which is what turns "we think it's
  cached" into evidence.

So: invalidation for freshness after *known* writes, TTL for a bounded
staleness ceiling after *unknown* ones. The cache is a dashboard read path
where 30 s of worst-case staleness is acceptable and 30 s *after a write*
is not — that asymmetry is exactly why both mechanisms exist.

### Volume justifications

- **`redisdata` (Redis AOF)** — *Ashar*: Redis holds three different
  durability interests: rate-limit windows (a restart without AOF hands every
  client a fresh 10/min allowance), the 30 s stats cache (cheap to rebuild,
  but AOF makes the rebuild a warm start instead of a stampede), and triage
  cache entries (24 h TTL). `--appendonly yes` on a named volume
  (`compose.yaml:103-105`) with `everysec` bounds data loss to about a
  second — trivial write volume, real anti-abuse continuity. Detail:
  `evidence/26` §4.
- **`pgdata` (Postgres PVC)** — *Ali*: Postgres is a StatefulSet, not a
  Deployment (`k8s/base/postgres.yaml:7`), with `volumeClaimTemplates`
  (`:70-72`) giving one stable volume per ordinal, forever — identity and
  storage move together, so a rescheduled `postgres-0` reattaches *its*
  data rather than any data. Proven, not asserted:
  `docs/evidence/21-postgres-persistence.txt` deletes the pod outright
  (uid change recorded) and every row survives on the replacement. A
  Deployment with a single shared PVC would corrupt the moment it scaled
  past one replica; the StatefulSet makes scaling safe by construction.
- **`ollama_models`** — *Ali*: caches pulled Ollama model weights at
  `/root/.ollama` (`compose.yaml:125`) so an opt-in local-model run does
  not re-pull ~800 MB on every `up` (the in-file rationale). Profile-gated
  (`compose.yaml:122`): default runs and CI never pay for it — the volume
  only materialises when someone explicitly opts into the ollama profile.

### Groq live rate limits, as observed

Honest answer: **not observed live in this project.** The real `LLM_API_KEY`
never left Ali's GitHub Secrets (placeholder in CI, `docs/AI-USAGE.md` M6);
local runs used `rules`/`simulated`. The 429 *behaviour* is therefore proven
against a fake client rather than against Groq: `is_retryable` accepts 429
(`llm.py:46`), the single retry fires on it (`test_llm_provider.py:66`), and
a 401/400 is never retried (`test_llm_provider.py:73`). If a live limit was
seen from CD or Ali's machine, Ali should append it here.

*Ali, appending 2026-09-27:* confirmed from my side — the real key has never
left this machine. GitHub Secrets holds a non-credential placeholder (set
up in M6, `docs/AI-USAGE.md`), the real key lives only in the gitignored
local `.env`, and CD injects the placeholder, so no live Groq call has ever
originated from CI either. Every local run I did used `rules`/`simulated`.
No live 429 observed anywhere in this project; if one ever is, the retry
single-fires per the proven policy and the evidence goes here.

### Build-context numbers — *Ali*

Backend **0.07 MB vs 195.72 MB**, frontend **0.21 MB vs 110.5 MB**
(`evidence/26` §2) — roughly 2800× and 500× reductions. Two mechanisms do
the work: `.dockerignore` excludes the bulk (`.git`, venvs,
`node_modules`, `.env` — the fastest byte to ship is the one never sent),
and deps-first layering keeps rebuilds incremental (dependency layers stay
cached until the lockfile changes). Why it matters three ways: CI minutes
(smaller contexts push/pull faster on every run), pull size on deploy, and
attack surface — `.dockerignore` is also what keeps secrets and toolchains
out of the image, which is why the submission gate checks it
(`scripts/check_submission.py`).

### Measured cache hit rate — *Ashar*

**0.75 (30 hits / 10 misses / 40 lookups), two identical runs.**
Method, reproduction command and the rotating-`X-Forwarded-For` detail:
`docs/TRIAGE.md` §3 and `docs/evidence/28-metrics-f4.txt` [1].
