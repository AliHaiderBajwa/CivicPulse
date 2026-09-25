# Rubric Checklist — 150 marks + 15 bonus

One box per rubric line. Tick only when **evidence exists** (code, screenshot, link, or doc section).

## A · Collaboration and version control — 15
- [ ] A1 main protected: no direct push, PR required, CI required, ≥1 approval; screenshot in docs/evidence/ — 3
- [ ] A2 two-branch model (dev + feature branches); no work committed directly to main — 2
- [ ] A3 ≥5 merged PRs, each linked to an Issue, each with a substantive review comment from partner — 4
- [ ] A4 ≥35 commits, conventional prefixes, neither partner below 35% (git shortlog -sn) — 3
- [ ] A5 one deliberate merge conflict on real code, resolved, with markers/resolution/merge evidence + 2–4 sentences on why that version won — 3

## B · Frontend — 18
- [x] B1 Submit view: validation, honest loading state, renders category, priority, AI summary and provider — 5
- [x] B2 Dashboard: pagination, filters, status transitions, server's 409 message verbatim — 5
- [x] B3 Stats view rendering aggregates and cache-hit state from X-Cache — 3
- [x] B4 runtime config — no baked-in API URL; one image runs in any environment — 3
- [x] B5 ≥5 meaningful component tests passing in CI — 2

## C · Backend — 25
- [ ] C1 all endpoints to contract, correct status codes, field-level validation errors — 7
- [ ] C2 four-layer separation: no SQL outside repositories, no business rules in routes — 4
- [ ] C3 status state machine as explicit transition table; invalid transitions 409 — 3
- [ ] C4 /health and /ready correctly distinguished; /health does not touch the database — 3
- [ ] C5 structured JSON logging to stdout with propagated request_id — 3
- [ ] C6 SIGTERM handled: in-flight requests drain before exit — 2
- [ ] C7 ≥14 backend tests, unit and integration, deterministic, coverage ≥65% — 3

## D · Data layer — 12
- [ ] D1 Alembic migrations; zero schema DDL in application startup code — 4
- [ ] D2 schema complete incl. triaged_by, ai_summary, triage_latency_ms, timestamptz — 3
- [ ] D3 two indexes, each justified by a named query in notes — 2
- [ ] D4 idempotent seed of ≥30 realistic complaints; running twice changes nothing — 3

## E · Cache layer — 10
- [ ] E1 /api/stats read-through cache, 30 s TTL, correct X-Cache header — 3
- [ ] E2 cache invalidated on write, not left to expire — 2
- [ ] E3 distributed Redis rate limiter on POST /api/complaints, 429 with Retry-After — 4
- [ ] E4 Redis AOF on a named volume, justification written down — 1

## F · AI layer — 25
- [ ] F1 TriageProvider interface with ≥3 working implementations selected by env var — 5
- [ ] F2 structured output requested and validated against Pydantic schema; malformed output rejected safely — 5
- [ ] F3 timeout, single jittered retry on retryable errors only, fallback to rules, triaged_by recorded — 6
- [ ] F4 content-hash caching of triage results with measured, reported hit rate — 3
- [ ] F5 prompt-injection guardrail plus a test submitting an injection attempt — 3
- [ ] F6 triage_latency_ms recorded and surfaced through /api/meta/providers — 2
- [ ] F7 PII/data-governance ADR: what leaves machine, to whom, why acceptable — 1

## G · Docker and Compose — 15
- [ ] G1 both images multi-stage, pinned base, non-root USER, exec-form CMD, cache-correct layer order — 4
- [ ] G2 .dockerignore per build context, before/after context sizes reported — 2
- [x] G3 two networks with internal: true; frontend provably cannot reach database — 4
- [x] G4 three named volumes, each justified; dev bind mount present and absent from prod — 2
- [x] G5 healthchecks on all services with depends_on: condition: service_healthy — 2
- [x] G6 compose.prod.yaml uses image: ${IMAGE_TAG}, no build:, no published DB or cache port — 1

## H · Kubernetes — 20
- [x] H1 namespace, Deployments, StatefulSet+PVC for Postgres, ClusterIP Services, Ingress routing / and /api — 5
- [x] H2 ConfigMap and Secret separated; committed manifests carry placeholders only — 2
- [x] H3 all three probes correct: liveness independent of DB, readiness dependent — 4
- [x] H4 resources.requests and limits set on every container — 2
- [x] H5 HPA v2 with tuned behavior + captured kubectl get hpa -w output + replicas-vs-load chart from real load test — 4
- [x] H6 VPA recommender mode, recommendations committed, requests updated in response, HPA/VPA conflict explained — 3

## I · CI/CD — 20
- [x] I1 ci.yml lint+typecheck+tests on every PR, configured as required checks — 4
- [x] I2 compose integration smoke job asserting real request path end to end — 3
- [x] I3 Trivy image scan and kubeconform manifest validation in CI — 3
- [x] I4 cd.yml with needs: gating publish, images pushed to GHCR tagged by commit SHA — 4
- [x] I5 Kubernetes deploy job on ephemeral cluster, waiting on rollout status and smoke-testing the Ingress — 3
- [x] I6 secrets from GitHub Secrets with scoped token and least-privilege permissions: block — 2
- [x] I7 evidence of a red pipeline blocking a merge, then green — 1

## J · Documentation, portfolio and reflection — 15
- [ ] J1 README.md: problem statement, badges, Mermaid architecture diagram, working one-command quickstart, API table, screenshots — 4
- [ ] J2 four ADRs: provider interface; frontend runtime config; deploy-by-SHA; PII/data governance — 4
- [ ] J3 docs/RUNBOOK.md: deploy, roll back, read logs, what to do when triage starts failing — 2
- [ ] J4 demo video ≤5 minutes, both partners speaking: clean clone → running system, AI triage, fallback, network isolation failing, HPA scaling, rollback — 3
- [ ] J5 docs/ENGINEERING-NOTES.md answering all eight §5.2 questions with file-and-line references — 2

## Bonus — capped at +15
- [ ] BN1 zero-downtime rolling update under live load, zero failed requests — +4
- [ ] BN2 GitOps (Argo CD or Flux) reconciling cluster from repo — +4
- [ ] BN3 deploy by image digest + Cosign signing/verification in CI — +3
- [ ] BN4 Prometheus scraping /metrics + Grafana dashboard screenshot — +2
- [ ] BN5 OpenTelemetry tracing frontend→backend→LLM — +2

## Submission gate (run before submitting)
- [ ] `python3 scripts/check_submission.py` clean
- [ ] no `.env` in git history
- [ ] cd.yml success link · GHCR SHA image links · video link · shortlog · hpa capture + chart
