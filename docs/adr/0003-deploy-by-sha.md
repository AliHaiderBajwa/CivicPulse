# ADR 0003: Deploy by commit SHA, never by moving tag

- **Status:** Accepted, 2026-09-25
- **Authors:** Ali Haider Bajwa (with opencode, disclosed in `docs/AI-USAGE.md`)
- **Context:** CS4032 Assignment 1 brief — deploy by SHA; `AGENTS.md` hard
  rule with a −8 deduction behind it; `release.yml` additionally publishes
  semver tags for humans.

## Context

Every push to `dev` must land on the cluster as *exactly the bytes CI
tested* — no rebuild-per-environment, no "latest means whatever pushed
last". At the same time humans want readable tags (`v1.2.3`, `latest`) for
pulling and browsing. The pipeline must serve both without letting the
human tags anywhere near the deploy path.

## Decision

**Build once, tag twice, deploy by SHA, assert at apply time.**

1. `build`/`publish` compile each image once and push two tags: the commit
   SHA (machine identity) and a `latest` alias (human convenience). Both
   resolve to the same digest — verified in
   `docs/evidence/22-cd-release-surface.txt`, never assumed.
2. Promotion is a tag *rewrite*, not a rebuild: the overlay's `newTag`
   placeholder becomes the commit SHA —
   `sed -i -E "s|newTag: .*|newTag: ${SHA}|"` on the selected overlay
   (`.github/workflows/cd.yml:293`).
3. The rendered manifest is asserted *at the point kubectl is handed it*:
   any `:latest` aborts the job, and every owned image must end in
   `:${SHA}` (`.github/workflows/cd.yml:296-303`). The −8 deduction is
   caught by code, not by discipline.

## Alternatives considered

- **Deploy `:latest`.** Ambiguous by construction: two deploys minutes apart
  can run different bytes under one tag, and rollbacks become guesswork.
  Rejected outright (−8).
- **Semver-only deploys.** Human-readable but untraceable: `v1.2.3` does not
  identify the commit or the CI run that tested it. Semver is still
  published (by `release.yml`, for humans pulling images) — it is just
  never what the cluster runs.
- **Digest pinning (`sha256:…`).** Strictly stronger than SHA tags and the
  obvious next step (bonus BN3). Not taken yet only because tag→digest
  resolution is already recorded per release and the marginal gain did not
  justify another moving part before the backend existed.

## Consequences

- Traceability is total: running image → commit SHA → CI run → SBOM, all
  recorded in the run summary (`docs/evidence/22-cd-release-surface.txt`).
- Rollback never rebuilds: fast path `kubectl rollout undo`, declarative
  path re-applying the previous SHA overlay (`docs/RUNBOOK.md` §2).
- The rule has exactly one enforcement point (the pre-apply assertion), so
  no future workflow edit can silently reintroduce `:latest` deployment.
