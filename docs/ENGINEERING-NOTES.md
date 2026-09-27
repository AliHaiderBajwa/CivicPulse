# ENGINEERING-NOTES — the eight questions (§5.2), with file-and-line refs

Split per the plan of record (`docs/PLAN.md` §7): Ashar owns the AI-layer,
backend and data answers; Ali owns the frontend runtime config, CI/CD and
Kubernetes answers. Refs point at the tree after PRs #25/#26 have merged.

---

### 1. Three laptop-vs-CI differences and the exact Dockerfile/manifest lines that freeze them — *Ali*

_Pending — Ali's answer, with the Dockerfile and workflow lines._

### 2. Position on the CI/CD maturity ladder (Lecture 03, slide 32), next rung and what it buys — *Ali*

_Pending — Ali's answer._

### 3. The exact line that guarantees build-once-deploy-many, and what breaks without it — *Ali*

_Pending — Ali's answer (deploy-by-SHA)._

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

_Pending — Ali's answer (k6 capture, `evidence/17`)._

### 6. Why VPA runs in Off mode, and the failure mode of Auto alongside HPA — *Ali*

_Pending — Ali's answer (`evidence/13`)._

### 7. Where the `internal: true` network leaves the LLM-calling service, and how you resolved it — *Ali writes, Ashar confirms*

_Ali's answer pending. My confirmation of the Compose side:_

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
- **`pgdata` (Postgres PVC)** — *Ali*: pending.
- **`ollama_models`** — *Ali*: pending.

### Groq live rate limits, as observed

Honest answer: **not observed live in this project.** The real `LLM_API_KEY`
never left Ali's GitHub Secrets (placeholder in CI, `docs/AI-USAGE.md` M6);
local runs used `rules`/`simulated`. The 429 *behaviour* is therefore proven
against a fake client rather than against Groq: `is_retryable` accepts 429
(`llm.py:46`), the single retry fires on it (`test_llm_provider.py:66`), and
a 401/400 is never retried (`test_llm_provider.py:73`). If a live limit was
seen from CD or Ali's machine, Ali should append it here.

### Build-context numbers — *Ali*

_Pending (both image contexts were measured in `evidence/26`; Ali owns the
frontend number and the interpretation.)_

### Measured cache hit rate — *Ashar*

**0.75 (30 hits / 10 misses / 40 lookups), two identical runs.**
Method, reproduction command and the rotating-`X-Forwarded-For` detail:
`docs/TRIAGE.md` §3 and `docs/evidence/28-metrics-f4.txt` [1].
