# RUNBOOK — commands, not prose

Split per `docs/PLAN.md` §7: Ali owns **deploy / rollback / read logs**,
Ashar owns **triage failing**. Sections marked _pending_ are the other
partner's; push to this branch or send the text.

---

## 1. Deploy — *Ali*

_Pending — Ali's section._

## 2. Roll back — *Ali*

_Pending — Ali's section._

## 3. Read logs — *Ali*

_Pending — Ali's section._

---

## 4. Triage is failing — *Ashar*

### 4.1 See it (one command each)

```bash
docker compose logs backend --tail 200 | grep -iE "triage|fallback"  # WARNING "triage fallback" = provider failing now
curl -s localhost:8000/api/meta/providers | jq                       # recent_triages[]: triaged_by, latency_ms, cached
curl -s localhost:8000/metrics | grep -E "triage_(fallback|cache|duration)"  # counters/histograms, no dashboard needed
```

`triaged_by` values, in order of suspicion: `rules:fallback` (provider
degraded — every such response was still a 201, that is by design),
`llm:groq` / `llm:ollama` (live model), `rules` / `simulated` (pinned, not
an incident).

### 4.2 Classify by `error_class` (in the WARNING log line / `triage_fallback_total` label)

| `error_class` | Meaning | Fix |
|---|---|---|
| `APITimeoutError` / `TimeoutError` / `APIConnectionError` | Provider unreachable or >10 s (`config.py:21`) | Check provider status; meanwhile nothing to do — fallback is holding. |
| `AuthenticationError` / `PermissionDeniedError` | Bad or rotated `LLM_API_KEY` (401/403, **never retried by design**) | Rotate the key (GitHub Secrets for CD, `.env` locally), redeploy. |
| `RateLimitError` | Groq quota (429) — one jittered retry already fired | Wait out the window or pin the cheap provider. |
| `BadRequestError` / `NotFoundError` | Model/deploy misconfigured (400/404, not retried) | Check `LLM_BASE_URL`/`LLM_MODEL` in the ConfigMap. |

### 4.3 Act (safe first, in order)

```bash
# 1. Pin the deterministic provider - no egress, no quota, same schema
#    (compose interpolates ${TRIAGE_PROVIDER:-simulated} at `up` time):
TRIAGE_PROVIDER=rules docker compose up -d backend       # Linux/macOS
# PowerShell: $env:TRIAGE_PROVIDER='rules'; docker compose up -d backend
kubectl -n civicpulse set env deployment/backend TRIAGE_PROVIDER=rules
kubectl -n civicpulse rollout status deployment/backend

# 2. Wrong answers stuck in the cache? Drop everything in this DB index
#    (FLUSHDB also resets rate-limit windows and stats - both rebuild at once;
#    a plain `restart` would NOT help: AOF reloads the old keys):
docker compose exec redis redis-cli FLUSHDB
kubectl -n civicpulse exec deploy/redis -- redis-cli FLUSHDB

# 3. Prove the fallback end-to-end (assignment's non-negotiable):
SIMULATED_FAIL_MODE=raise TRIAGE_PROVIDER=simulated docker compose up -d backend
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/api/complaints -H 'content-type: application/json' -d @complaint.json
#    -> 201 and body.triaged_by == "rules:fallback"; metrics triage_fallback_total +1
```

### 4.4 What must never happen

- A 5xx to the citizen because a provider failed — `except Exception` in
  `triage_orchestrator.py:67` converts every provider failure to
  `rules:fallback`. If you see 500s on POST, it is **not** the LLM: look at
  the DB/Redis (`/health` vs `/ready` first).
- Boot with the database down now fails fast by design (lifespan migration,
  `4416cd1`): container exits non-zero, orchestrator restarts. That is the
  sanctioned abort path, not a crash loop to debug.

### 4.5 Kubernetes pin (temporary)

```bash
kubectl -n civicpulse set env deployment/backend TRIAGE_PROVIDER=rules
kubectl -n civicpulse rollout status deployment/backend
kubectl -n civicpulse rollout undo deployment/backend   # back to ConfigMap value
```
