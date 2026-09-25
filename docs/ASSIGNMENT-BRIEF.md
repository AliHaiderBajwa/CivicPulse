# Assignment Brief — CivicPulse (CS4032 A1)

Reference digest of the assignment PDF. **Contracts in §2 of the PDF are what gets tested.**
Team 2 · 150 marks + 15 bonus · A–J rubric.

## 1. Product

Municipal complaint intake → AI triage (category, priority, one-line summary) → live ops dashboard.
Five containers, one command locally; K8s cluster in CI as a second command; push to main tests, builds, scans, deploys, undoes.

## 2. System contracts

### Frontend (React 18 + Vite + TS, served by nginx:alpine multi-stage)
- Views: **Submit** (validation mirrors server, honest loading, shows category/priority/summary/**provider**), **Dashboard** (paginated, filters category/priority/status, advance status, server 409 message verbatim), **Stats** (aggregates + `X-Cache` badge).
- Runtime config: NO baked-in API URL. Relative `/api` + nginx proxy (ADR 0002). Typed client from OpenAPI. Error boundary. No secrets in the bundle.

### Backend (FastAPI + Pydantic v2) — four layers, arrows one way
`routes/` HTTP only → `services/` business rules → `repositories/` all SQL → `providers/` outbound (LLM, cache) behind interfaces.

Endpoints (§2.2 table):
| Method | Path | Notes |
|---|---|---|
| POST | /api/complaints | validate→triage→persist; 201; 400 field-level; 429 rate limit |
| GET | /api/complaints/{id} | 200/404 |
| GET | /api/complaints | filters + pagination (page, page_size ≤ 100) + total |
| PATCH | /api/complaints/{id}/status | state machine; invalid → 409 naming attempted transition |
| GET | /api/stats | Redis-cached 30 s, X-Cache: HIT |
| GET | /api/meta/providers | active provider + last 20 triage outcomes (provider, latency ms, fallback y/n) |
| GET | /health | liveness, **must not touch DB** |
| GET | /ready | 200 iff Postgres AND Redis reachable; 503 names failed dependency |
| GET | /metrics | Prometheus: request count, latency histogram, triage latency, fallback counter |

Domain rules:
- State machine as **explicit transition table**: open→in_progress→resolved; open→rejected; in_progress→rejected; resolved/rejected terminal. Everything else 409.
- SIGTERM graceful shutdown: stop accepting, drain in-flight, close pools, exit.
- JSON structured logs to stdout, every line carries `request_id` (from X-Request-ID, generate if absent). One WARNING per triage fallback with complaint id, provider, error class.
- Validation errors: **400** (not 422) with `{"detail":[{"field","message"}]}`.

### Data (PostgreSQL 16, Alembic only — no DDL in app startup)
Columns: id UUID server-gen · text 10–2000 (CHECK in DB too) · location 3–200 · reporter_contact nullable · category enum (water·electricity·sanitation·roads·streetlights·other) · priority enum (high·normal·low) · status enum (open·in_progress·resolved·rejected, default open) · ai_summary nullable ≤140 · triaged_by (llm:groq·llm:ollama·rules·rules:fallback) · triage_latency_ms int · created_at/updated_at timestamptz UTC.
Indexes: **(status, priority)** and **created_at** — each justified by a named query in notes.
Seed: ≥30 realistic Urdu-influenced English complaints, spread across categories, idempotent (run twice → row count unchanged).
Persistence: `compose down/up` keeps rows; deleting the Postgres pod keeps rows.

### Cache (Redis 7, two jobs)
1. Read-through cache for /api/stats: TTL 30 s, X-Cache HIT|MISS, **invalidate on write** (explain at viva why both TTL and invalidation).
2. Distributed rate limiter by client IP on POST /api/complaints: 429 + Retry-After. Must be in Redis (HPA → N pods × in-process limit = N× traffic).
AOF on a named volume + written justification.

### AI layer
```python
class TriageResult(BaseModel):  # category, priority, summary ≤140, confidence 0..1
class TriageProvider(Protocol):
    name: str
    def triage(self, text: str, location: str) -> TriageResult: ...
```
Four implementations via `TRIAGE_PROVIDER`: **LLMTriage** (Groq, free tier), **OllamaTriage** (offline container), **RuleBasedTriage** (deterministic keywords), **SimulatedTriage** (deterministic CI fake, configurable failure injection).

Engineering (where the marks are):
1. Structured output requested (JSON mode/tool/schema) **and** validated with Pydantic anyway; reject prose, fences, out-of-enum, >140-char summaries.
2. Hard 10 s timeout on every call.
3. Retry **once** with jitter — timeout/429/5xx only. Never retry 400.
4. Fallback → RuleBasedTriage, `triaged_by="rules:fallback"`, WARNING log.
5. Content-hash cache in Redis, 24 h TTL; report measured hit rate.
6. API key from env/Secrets only — never logged, never in repo.
7. Prompt-injection guardrail: complaint text = untrusted data, delimited, output constrained to enum + test that injection attempt still yields schema-decided category.

Determinism: CI pinned to SimulatedTriage; inject always-raise and malformed-JSON providers in tests.
**The test that must exist:** always-raise provider → POST /api/complaints → 201 + `triaged_by == "rules:fallback"`.

## 3. DevOps

**Images:** both multi-stage, pinned, non-root, exec CMD; backend HEALTHCHECK; .dockerignore each; report context sizes before/after + stage sizes (frontend ≤ ~60 MB).

**Compose:** two networks — `edge` (bridge), `internal` (bridge, `internal: true`). frontend→edge only; backend→both (LLM egress lives here — explain in notes Q7); db/cache→internal only. Prove `exec frontend ping database` fails.
Three volumes, **each justified**: pgdata, redisdata (AOF), ollama_models. Dev bind mount for hot reload + the sentence in each compose file about why it's right for dev / wrong for prod.
Healthchecks all services, `depends_on: condition: service_healthy`, `${...}` creds, .env.example committed, .env ignored, pinned tags, restart: unless-stopped, deploy.resources limits.
`compose.yaml` (dev, `build:`) · `compose.prod.yaml` (deploy, `image: …${IMAGE_TAG}`, **no build:**, no published DB/cache ports).

**Kubernetes** (k3d/kind, Kustomize base + overlays/dev + overlays/prod, namespace `civicpulse`):
Deployments ×2 (≥2 replicas) · **StatefulSet postgres + volumeClaimTemplates** · redis Deployment+PVC · Services ×4 ClusterIP · Ingress `/`→frontend, `/api`→backend, one host · ConfigMap · Secret placeholders only · HPA v2 (min2/max10, CPU 60%, scaleDown 300 s, scaleUp 0 s) · PDB minAvailable 1 · VPA updateMode Off.
Probes: startup `/health` failureThreshold 30 period 2; liveness `/health` (no DB); readiness `/ready` (DB-dependent).
Rolling update: maxSurge 1, maxUnavailable 0, terminationGracePeriodSeconds, preStop sleep.
**Requests+limits on every container** (HPA divides by request — no request = `<unknown>/60%` forever).
Evidence: `kubectl get hpa -w` capture, replicas-vs-load chart from k6, HPA lag paragraph, VPA loop (guess → load → describe → update requests → re-run), persistence proof (delete postgres pod).

**CI/CD** — branches: `dev` work, `main` deployable, protected (PR + 1 approval + required checks).
- `ci.yml` (PR→main, push→dev): lint-and-type (ruff+mypy / eslint+tsc) · test-backend (coverage ≥65%, TRIAGE_PROVIDER=simulated) · test-frontend (Vitest ≥5) · build (NO push) · scan (Trivy HIGH/CRITICAL, fail if fixed) · manifests (kustomize | kubeconform) · integration (compose up → /ready → POST → GET → assert category → X-Cache MISS→HIT → down -v).
- `cd.yml` (push→main): test → build-push (needs: test; GHCR tagged `${{ github.sha }}` + latest; Syft SBOM; digest output) → deploy-k8s (needs: build-push; ephemeral kind; SHA overlay; rollout status; smoke test Ingress; kubectl get hpa).
- `release.yml` (tag v*): semver tags + release notes.
- Non-negotiables: `needs:` everywhere publishing/deploying · deploy by SHA (digest for bonus) · GitHub Secrets only · least-privilege `permissions:` block · actions pinned @v4+ · red-pipeline-blocks-merge evidence.
- Rollback: `kubectl rollout undo` (fast) vs re-apply previous SHA overlay (declarative) — explain when to use each (RUNBOOK).

## 4. Docs & submission

README (problem, badges, Mermaid, one-command quickstart, API table, screenshots) · 4 ADRs (provider interface, frontend runtime config, deploy-by-SHA, PII/data governance) · RUNBOOK · ENGINEERING-NOTES (8 questions, file:line refs) · TRIAGE.md · AI-USAGE.md (honest, specific) · demo video ≤5 min both partners speaking · docs/evidence/ screenshots · `scripts/check_submission.py` clean.

Submission: repo URL · successful cd.yml run link · both GHCR images w/ SHA tags · video link · `git shortlog -sn` · `kubectl get hpa -w` capture + chart.

## 5. Automatic deductions (scan before every push)

−20 .env/key in history · −15 key in K8s manifest (base64 counts) · −8 unpinned image · −8 localhost service-to-service · −8 frontend reaches DB · −8 published DB/cache port (compose.prod) or NodePort/LoadBalancer DB · −8 ungated publish/deploy · −8 deploying :latest · −8 Postgres Deployment w/o PVC · −5 direct push to main · −5 broken README quickstart.

## 6. Value order when behind

**F (AI, 25) > C (backend, 25) > I (CI/CD, 20) > H (K8s, 20).** Never skip the fallback test. Late submissions not accepted.
