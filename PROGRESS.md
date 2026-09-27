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

## M4 — P4: CI pipeline green ×7 + required checks (Ali + AI agent)

**Expected:** `ci.yml` with lint/type, backend tests (cov ≥65), frontend tests, image build, Trivy scan, kubeconform manifest validation, and a compose integration smoke job — running on every PR, configured as required status checks, with red→green evidence.

**Achieved:**
- `.github/workflows/ci.yml` — 7 jobs: `lint-and-type`, `test-backend` (pytest cov ≥65), `test-frontend` (15 Vitest), `build` (no push), `scan` (Trivy, HIGH/CRITICAL, ignore-unfixed), `manifests` (kustomize prod → kubeconform -strict + CRDs-catalog schema, 16/16), `integration` (compose stub/full paths `hashFiles`-gated, real request path).
- **Two red runs, diagnosed and fixed honestly:**
  1. `36157508384` — plain YAML scalar ate a ` #` (comment) mid-string + trivy-action needs the `v` tag prefix → block scalar + `@v0.36.0`.
  2. `36157889109` — Trivy gate did its job: **40 fixable CVEs (38 HIGH, 2 CRITICAL)** in `nginx:1.27-alpine` → base bumped to pinned `nginx:1.30.5-alpine3.24` + `apk upgrade --no-cache`.
- **Green run `36159826654` (37f1f1c): all 7 jobs success.**
- Required status checks (all 7 contexts) now enforced on **`dev`** (no review gate — green-only merges) and **`main`** (PR + 1 approval + checks).
- Evidence written: `docs/evidence/09-ci-red-to-green.txt`; AI disclosure: `docs/AI-USAGE.md`.
- Rubric: ticked B5, I1, I2, I3.

**Evidence:** `docs/evidence/09-ci-red-to-green.txt`; `gh run view 36159826654`; branch protection API responses; commits `78408bb`, `bc52b78`, `37f1f1c`.

**Next:** live red-blocks-merge demo for I7; P5 k3d bring-up + deploy of `k8s/overlays/dev` (pause courier containers first — ask user); then P6 `cd.yml`.

## M5 — P5: Kubernetes stack live on k3d + autoscaling evidence (Ali + AI agent)

**Expected:** `k8s/` base + overlays applied to a real cluster; three probes correct on every workload; resources everywhere; HPA v2 scaling on real load with `-w` capture and replicas-vs-load chart; VPA recommender recommendations applied to manifests.

**Achieved:**
- **k3d cluster `civicpulse`** (k3s v1.35.5, single node, host :8080→Traefik; host :80 was taken by system apache2 — never touched). Images imported via `ctr` (k3d's importer silently skipped an OCI-index image once — direct `docker save | ctr import` used).
- **Deployed `k8s/overlays/dev`**: namespace, ConfigMap, Secret (placeholders only in git — verified `git grep gsk_` empty, `.env` ignored), backend/frontend Deployments (RollingUpdate maxUnavailable 0, 3 probes, requests+limits), postgres **StatefulSet + volumeClaimTemplates**, redis Deployment + PVC, 4 ClusterIP Services, Ingress (one host; `/`→frontend, `/api`→backend), HPA v2, VPA (Off), PDB. kubeconform 16/16 via CI.
- **VPA installed** — upstream CRDs are still apiextensions/v1beta1; used `vpa-v1-crd-gen.yaml` from `kubernetes/autoscaler` tag `vertical-pod-autoscaler-1.7.1` (recommender only, no updater/admission). Recommendation: **cpu 93m / memory 250Mi** → applied to `k8s/base/backend.yaml` (requests 100m→93m, 128Mi→250Mi), recommender `RecommendationProvided=True`.
- **Ingress smoke:** GET `/` 200, GET `/api/stats` 200, POST `/api/complaints` **201** (category `streetlights`), PATCH 409 body verified. (First 404 scare was my curl missing the `Host:` header.)
- **Stub rewritten to the full contract** (was 501 on POST): POST w/ 400 validation + 429, GET list/by-id, PATCH w/ 409 on invalid transition, stats X-Cache, threaded server. Integration CI job now asserts POST→GET→PATCH 200→PATCH 409.
- **Two load-test bugs found & fixed (kept as lessons):**
  1. Early 429/404 returns didn't drain the request body → keep-alive connections poisoned → next request parsed body as request line → **400 storm (68% failure)**. Fix: always read body first. k6 rerun: **100% checks, 0.00% failed, 79 652 requests**.
  2. Rate-limit keys collided behind Traefik (strips untrusted XFF): dev overlay raises `RATE_LIMIT_PER_MIN` to 1 000 000 for synthetic load only; **base/prod keep 10/min**, proven separately (10×201 then 429, `docs/evidence/11-rate-limit.txt`).
- **HPA cycle on real load:** 2→6→10 replicas at CPU 446%/60% during k6 (peak 522 rps), hold, 10→2 after load, burst blip 2→3→2. Captured live `kubectl get hpa -w` stream and 5s-sampled CSVs; chart `docs/evidence/18-hpa-load-chart.png`.
- Frontend crash-restarts diagnosed: DNS-at-startup race with Service creation during first apply — clean re-rollout = **0 restarts**.

**Evidence:** `docs/evidence/11-rate-limit.txt`, `12-k8s-probes-resources.txt`, `13-vpa.txt`, `14-config-secret-separation.txt`, `15-hpa-watch.txt`, `16-hpa-collect.csv`, `17-k6-rps.csv`, `18-hpa-load-chart.png`; k6 logs 100% green.

**Next:** commit M5 artifacts; P6 `cd.yml` (I4/I5/I6); save k3d bring-up as `scripts/k8s-up.sh`; then P7 docs/J-block (README, diagrams, screenshots) and watch for Ashar's backend PRs.

## M6 — P6: CD pipeline green end to end (Ali + AI agent)

**Expected:** `cd.yml` gating publish with `needs:`, images pushed to GHCR tagged by commit SHA, a Kubernetes deploy on an ephemeral cluster that waits on rollout status and smoke-tests the Ingress, and secrets supplied from GitHub Secrets under a scoped token with least-privilege permissions.

**Achieved:**
- **`.github/workflows/cd.yml`** — `build` → `publish` → `deploy-k8s`, each gated by `needs:`. `build` compiles both images with `push: false`; `publish` pushes **only** `:${github.sha}` (never `latest`) and then asserts both tags exist in the registry via `docker manifest inspect`; `deploy-k8s` may not start unless that assertion passed.
- **Ephemeral kind cluster** (kind v0.30.0, pinned) with `extraPortMappings 80:80`, pinned ingress-nginx kind provider (`controller-v1.12.1`), node labelled `ingress-ready=true`, the published SHA images `kind load`ed, then `dev` overlay on `dev` / `prod` overlay on `main`.
- **Deploy by SHA:** the overlay's `newTag` placeholder is rewritten to the commit SHA and the rendered `image:` lines are echoed as proof before apply. Rendered manifests asserted locally: no `latest`, no `prod-0000000` survives.
- **Rollout + smoke (I5):** `rollout status` for `deploy/backend`, `deploy/frontend`, `sts/postgres`, `deploy/redis`; then Ingress smoke — `GET /` 200, `GET /api/stats` 200, `POST /api/complaints` **201** with `id` + `triaged_by`.
- **I6 least privilege:** top-level `permissions: {}`; `build` = `contents:read`; `publish` = `+packages:write`; `deploy-k8s` = `+packages:read` (pull only). `LLM_API_KEY` read from GitHub Secrets (repository secret set to a **non-credential placeholder**; the real Groq key stays in the local `.env`). The committed placeholder Secret is replaced at deploy time with a freshly generated DB password; only key *names* are printed.
- **Three real defects found by running it, all fixed:**
  1. `IMAGE_BASE` unbound in the registry assertion (a rewrite had dropped its `env:`) → `set -u` killed publish *after* both images had pushed; `deploy-k8s` correctly stayed skipped, so nothing deployed. Fixed by restoring the `env:`.
  2. Same class of bug one job later: the `kind load` step had lost its `env:` too, so `docker` got an empty ref and exited 125. Fixed, and a mechanical audit now resolves every `${VAR}` in every `run:` block before push.
  3. **A fresh cluster could not deploy at all**: `kubectl apply` died with `no matches for kind "VerticalPodAutoscaler"` because the VPA CRD lived only in my local k3d cluster. The CRD is now **vendored** (`k8s/crds/`, from `kubernetes/autoscaler @ vertical-pod-autoscaler-1.7.1`) and installed in a separate apply stream before the overlays, because kubectl cannot map a custom resource in the same stream that installs its CRD. Re-applying locally reports `unchanged`, so the vendored copy matches what was installed by hand. The recommender (RBAC + Deployment) is vendored under `k8s/vpa/` too — kept out of the base overlay on purpose, since it needs `metrics.k8s.io` and a throwaway kind cluster has no metrics-server.
- `actionlint v1.7.7` runs clean over both workflows; it caught a genuine `needs.build` vs `needs.publish` scoping bug that would have sent an empty image name to the deploy job.
- CI `manifests` now validates the vendored dirs too: `k8s/vpa` strict (**26/26 valid**); `k8s/crds` is **schema-skipped on purpose** — kubeconform's default catalogue ships no `apiextensions.k8s.io` schema (404 at every k8s version), so the honest proof is the CD job installing the CRD into a live API server and waiting for `Established` (`docs/evidence/19-cd-deploy.txt`).

**Red→green trail (honest):** `36169675730` publish failed on the unbound `IMAGE_BASE` → `36169949655` deploy failed with docker exit 125 → `36170243505` deploy failed on the missing VPA CRD → **`36170624771` build+publish+deploy-k8s all success**.

**Evidence:** `docs/evidence/19-cd-deploy.txt` (captured by `scripts/cd-evidence.sh`, which asserts the four facts that make the capture meaningful: SHA tags, rollouts, smoke OK, secret keys); run `36170624771`; CI `36170624655` (manifests job updated).

**Next:** tick I4/I5/I6; save the k3d bring-up as `scripts/k8s-up.sh`; then P7/J-block (README, Mermaid diagrams, screenshots, runbook) and the AI layer, watching for Ashar's backend PRs.


## M7 — release surface, deploy guard, and the handoff fix (2026-09-25)

**Expected:** the brief's CI/CD shape satisfied — a `test` gate ahead of publish,
`latest` published alongside the SHA, Syft SBOMs, recorded digests, a
`release.yml` on `v*` tags, and the three missing §4 docs blocks still open.

**Achieved:**
- **Handoff correctness (the important one).** Re-reading `docs/ASHAR-HANDOFF.md`
  against the brief found it claiming *"compose.yaml already prefers `backend/`
  over `tools/stub-backend`"*. **It does not** — `compose.yaml` hardcodes
  `build: context: ./backend`, so `docker compose up` fails until that directory
  exists; `compose.stub.yaml` is the variant that runs today. A false promise to
  a partner is worse than a missing feature, because he would have lost the first
  hour of his first day. The handoff now describes the real mechanism per surface
  (CI and CD switch on `hashFiles`; Compose does not switch at all), and the
  README quickstart states which command works now and which becomes the only
  command once `backend/` lands.
- **Persistence proof (brief §3, previously missing).**
  `docs/evidence/21-postgres-persistence.txt`: a row is written, the pod is
  deleted outright (uid `51430caf` → `934b4122`), the StatefulSet replaces it, and
  the rows are still there. The **first** capture of this matched no pods
  (wrong selector), deleted nothing and "passed" vacuously; it was discarded
  rather than filed as evidence, and the real run confirms a different pod uid.
- **`cd.yml` reshaped to the brief:** `test` → `build` → `publish` → `deploy-k8s`,
  every hop `needs:`-gated. The backend half of `test` is gated on
  `hashFiles('backend/pyproject.toml')` so it skips cleanly until Ashar's
  directory exists. `publish` now carries `:${github.sha}` **and** a `latest`
  alias — the brief asks for both, and `AGENTS.md` forbids *deploying* `:latest`,
  not publishing it, so the two rules are satisfied rather than traded off.
- **Syft SBOMs** (SPDX JSON) for both images, and **digests** recorded to the run
  summary. Verified in the registry: `latest` and the SHA resolve to the *same*
  digest for both images, so the alias can never drift into a different build.
- **Deploy-by-SHA guard.** `deploy-k8s` now reads the rendered manifest it is
  about to apply and refuses to continue if it contains `:latest`, or if any
  `${IMAGE_BASE}` image is not pinned to the commit SHA. The −8 deduction is
  caught at the point `kubectl` is handed the file, instead of trusting a `sed`.
- **`release.yml` (tag `v*`):** semver validation → publish semver + 2-part + SHA
  tags → SBOMs → GitHub Release with notes and an image digest table. It
  publishes but **never deploys**; a release means "this commit is a version".
- **Two defects found by running it, both fixed:**
  1. The first version of the guard demanded *every* image be pinned to our
     commit SHA, which also rejected `postgres:16-alpine` and `redis:7-alpine` —
     third-party images correctly pinned by upstream tag. Caught by run
     `36175736931` going red, not by a green pipeline. The guard is now scoped to
     our own images and was verified against the real overlay (passes) plus three
     tampered variants (`:latest`, one image moved to `main`, `postgres:latest` —
     all rejected).
  2. The first semver regex rejected `v1.2.3-rc1` while the same file's
     `prerelease:` flag assumed prereleases could exist, so **prereleases were
     uncuttable**. Replaced with the full semver 2.0.0 grammar; checked against
     12 cases.

**Evidence:** run **`36176361020`** (test/build/publish/deploy all success),
`docs/evidence/22-cd-release-surface.txt` (job chain, digest equality for the
alias, SBOM artifact sizes), `docs/evidence/21-postgres-persistence.txt`.

**Next:** ADRs, RUNBOOK, ENGINEERING-NOTES (Ali's four answers), then
`scripts/check_submission.py`; on Ashar's first PR, add the `X-Cache MISS→HIT`
assertion to the integration job, which only becomes meaningful once his Redis
cache exists.


## M8 — A5 deliberate conflict produced and resolved, PR #21 awaiting Ashar review (2026-09-26)

**Expected:** per issue #19 and `docs/PLAN.md` A5 — one deliberate conflict on real
code, resolved, with markers/resolution/merge evidence + rationale. Ashar opened
PR #20 (backend healthcheck `10s→5s`); Ali reviewed it (verified the 5s claim
against the database/cache 5s cadence at compose.yaml:89/:111), approved, and
merged it as `7c5de58` with `--merge` to keep the topology.

**Achieved:**
- Ali branched `feat/healthcheck-conflict-ali` from the **pre-merge** base
  `07648b1` (branching from updated dev would have fast-forwarded — the one way
  this exercise fails), changed the same line to `30s` (`0a69916`), pushed, and
  merged `origin/dev` → genuine `CONFLICT (content)` on `compose.yaml:65`, with
  `<<<<<<< HEAD (30s)` vs `>>>>>>> origin/dev (5s)` exactly as git left them.
- Resolved to **5s** (`c37ef00`, a true two-parent merge): 5s matches the
  db/cache cadence, detects a dead backend in ~15s not ~45s, costs one localhost
  HTTP request, and `start_period: 15s` still absorbs slow startups. 30s saved
  nothing measurable.
- Evidence per #19: `docs/evidence/02-conflict-markers.{txt,png}`,
  `03-conflict-resolved.{txt,png}`, `04-merge-graph.{txt,png}`. Method disclosed:
  this machine has no GUI screenshotting, so the `.txt` files are byte-exact
  terminal captures and the `.png` files are renders of those exact bytes
  (Pillow + DejaVu Sans Mono, one PNG visually verified before commit). The raw
  states additionally live in history: `0a69916` vs `ac5bf30` vs `c37ef00`.
- PR **#21** opened into `dev` with the rationale in the body, `ashar1x`
  requested as reviewer, all 8 checks green. Merge waits for his approval —
  his review is the second half of the pair evidence, so A5 stays unticked
  until then.

**Evidence:** PR #20 (merged `7c5de58`, Ali's approving review on record), merge
commit `c37ef00`, PR #21 (open, checks green).

**Next:** Ashar reviews #21 → merge → tick A5, close #19 → continue J-block
(ADRs, RUNBOOK, ENGINEERING-NOTES) and `scripts/check_submission.py`.


## M8 close-out — PR #21 approved by Ashar, merged, A5 ticked (2026-09-26)

**What changed since the M8 entry:** `ashar1x` approved PR #21 and it merged as
`4e1d80d`. `dev` history now shows the full A5 story in topology: Ashar's
`ac5bf30` (5s) via PR #20, Ali's `0a69916` (30s) from the pre-merge base, the
two-parent resolution `c37ef00` (5s wins, rationale in body), evidence
`02/03/04` (txt + png), and both PR review threads. `compose.yaml:65` on `dev`
is `interval: 5s`; the stack validates (`docker compose config` clean).
Checklist A5 ticked; issue #19 was already closed. Nothing about the conflict
was re-staged or re-worded after the fact — the evidence files are byte-identical
to what was captured mid-conflict.

**Next:** J-block (ADRs, RUNBOOK, ENGINEERING-NOTES) and
`scripts/check_submission.py`; Ashar's backend PRs (#1 first) are the main event.

## M9 — A5 ticked, Ashar's environment stood up, issue #1 skeleton = PR #22 (2026-09-26)

**Expected:** Ashar closes out A5 by reviewing #21, brings up his local toolchain
from a cold start, then implements issue #1 per `Ashar_Track` Step 1 and ships it
as a reviewable PR.

**Achieved:**
- **A5 closed:** reviewed PR #21 as `@ashar1x` with a verified (not rubber-stamped)
  review — confirmed `c37ef00` is a true two-parent merge (`0a69916` + `7c5de58`),
  markers captured pre-staging, net `compose.yaml` diff vs dev is zero because the
  resolution adopts the already-reviewed 5s — approved and merged `4e1d80d`.
  **A5 ticked.**
- **Environment:** Docker Desktop started; uv-managed CPython 3.12.13 →
  `backend/.venv`; 34 runtime + 21 dev dependencies pinned in
  `backend/requirements{,-dev}.txt`; dev Postgres 16 + Redis 7 containers on
  loopback with a separate `civicpulse_test` database; assignment PDF re-extracted
  (pypdf, 26 pages) and diffed against `docs/`-adjacent `SCDA1.md` — no content
  delta (the PDF genuinely has no §5.6).
- **Issue #1 (PR #22):** all nine endpoints with the frozen contract's operationIds;
  contract-named Pydantic schemas so `npm run gen:api` output keeps `client.ts`
  compiling; deterministic idempotent exporter that drops FastAPI's phantom 422
  (runtime is 400 via `routes/errors.py`) and forces the contract-shaped
  `ValidationError` before FastAPI's same-named internal model can win the
  collision; field-level 400s; JSON stdout logs carrying `request_id`;
  request-context middleware (`x-request-id` in, Prometheus HTTP metrics out);
  `/health` real, `/metrics` live, `/ready` + complaint bodies 501 until #4–#6.
- **Local gates:** `ruff check .` clean, `mypy app --ignore-missing-imports`
  clean, exporter hash-stable across runs, `tsc --noEmit` green after
  `gen:api`, vitest 15/15.

**Evidence:** PR #20 (merged `7c5de58`), PR #21 (merged `4e1d80d`, my approving
review on record), PR #22 (open), commits `08ee4d3..c84662e`.

**Next:** #3 Alembic migration + idempotent seed → #4 triage providers (incl.
always-raise → 201 `rules:fallback`) → #5 complaint API/state machine → #6 Redis
cache + limiter → #10 suite (the PR that activates `test-backend` and the real
integration smoke) → #17 wiring → #18 docs.

## M10 — PR #22 merged, Sonar gate fixed, PR #23 green and clean (2026-09-26)

**Expected:** the A5 → #1 → #3 train keeps moving: Ali reviews #22, the Sonar
Quality Gate stops failing, and #3's PR survives dev moving underneath it.

**Achieved:**
- **SonarCloud fixed:** the first analysis failed `C Security Rating on New
  Code` on two `pythonsecurity:S8707` findings (the exporter took its output
  path from `sys.argv`). The argument is gone entirely — the destination is
  derived from `__file__` and the output stayed byte-identical (verified by
  re-running the exporter against the committed file) — plus the duplicated 501
  literal was hoisted. Re-analysis green on #22 and #23.
- **dev moved twice mid-flight** (Ali's direct A5 close-out `d5f7775`, then the
  PR #22 merge `e4994ff`): both docs collisions resolved by keeping *both*
  partners' PROGRESS entries and taking dev's richer A5 annotation; docx
  regenerated each time. Ali independently resolved the same collision on #22
  — merged content matched ours, which is the point of doing it two ways.
- **PR #22 merged** (`e4994ff`): issue #1 skeleton is on dev.
- **PR #23** (issue #3) re-verified after syncing the merged dev: 8/8 CI checks
  + Sonar green, `mergeable=clean`.
- AI-USAGE M9 disclosure row restored (Ali's resolution on the branch had
  dropped it — disclosure never optional).

**Evidence:** `e4994ff` (PR #22 merge), PR #23 checks at `821f192`,
`docs/evidence/23-data-layer-proof.txt`, Sonar analyses for both PRs.

**Next:** Ali reviews #23 → merge → tick D1–D4 → issue #4 triage providers
(always-raise → 201 `rules:fallback` is the non-negotiable test) → #5, #6, #10.

## M11 — complaints/stats/meta/health routes live, 12 rubric boxes ticked (2026-09-26)

**Expected:** issue #5+#6's application layer lands — routes wired through to the
services, verified over real HTTP against cp-pg/cp-redis, contract untouched,
with enough evidence to tick the C/E/F boxes this batch actually earns.

**Achieved:**
- **Routes implemented** on `feat/complaints-api` (stacked on #4 + #3 branches):
  `complaints` (create/list/get/status), `stats`, `meta/providers`, `health`
  (`/ready` returns 503 `degraded` when either dependency is down), plus the
  Redis rate-limit dependency on POST. DI in `deps.py` uses `Annotated` (ruff
  B008-clean); routes return service results and let `response_model` serialize
  (mypy-clean, contract export byte-identical).
- **End-to-end proof** (`docs/evidence/25-complaints-api.txt`): 201 with
  `triaged_by:"simulated"` and triage-derived category; field-level 400s;
  404/409 messages verbatim; stats MISS→HIT→MISS-invalidation; 3×201 then 429
  with `retry-after: 60`; `/health` **200 while Postgres auth is broken** and
  `/ready` 503 `degraded` (liveness/readiness split, C4's whole point);
  `SIMULATED_FAIL_MODE=raise` → **201 + `triaged_by:"rules:fallback"` + one
  WARNING JSON line** (hard rule held on the request path, not just in unit
  tests); structured access logs with `request_id` echoed as `x-request-id`.
- **Gates:** ruff 0, mypy 0 (39 files), exporter re-run → `git diff
  docs/openapi.json` empty after implementing everything.
- **12 checklist boxes ticked with pointers:** C1–C4 (C2 grep proof: no SQL
  outside repositories), E1–E3, F1–F3, F5, F6. F4 deliberately left open
  (still owes the duplicate-submit hit-rate script + number).
- Two PS gotchas avoided after earlier incidents: curl bodies sent via `-d
  @file` (PS 5.1 mangles embedded quotes), all UTF-8 edits via the edit tool.

**Evidence:** commits `ac1ed2d` (services), `270c4b7` (DI), `bbd6cef` (routes),
`9d2e2cd` (evidence 25); `docs/evidence/25-complaints-api.txt`.

**Next:** Dockerfile + `.dockerignore` + SIGTERM drain proof (C6) + compose AOF
(E4) → push, PR `Closes #5, Closes #6` (Dockerfile rides along per Ali's
ruling) → then #10 test suite, #17, #18 docs.

## M12 — backend image + SIGTERM drain + AOF verified, G/C6/E4 boxes ticked (2026-09-26)

**Expected:** the #5+#6 PR gets its image (Ali's ruling: Dockerfile lands with
working endpoints, and the endpoints are done), the graceful-shutdown claim
gets proven rather than asserted, and the compose AOF gets pointed at.

**Achieved:**
- **`backend/Dockerfile`** (multi-stage, `python:3.12.13-slim-bookworm` exact
  patch tag, deps layer before source, numeric `USER 10001:10001`, exec-form
  CMD with `--timeout-graceful-shutdown 20`, urllib HEALTHCHECK) +
  `.dockerignore`. Cold `--no-cache` build exit 0; image 74.1 MB.
- **Context sizes reported both ways, both images** (G2): backend 48 files /
  0.07 MB with ignore vs 8129 / 195.72 MB without (149 MB = `.venv`);
  frontend 19 / 0.21 MB vs 9476 / 110.5 MB. A fresh `buildx` builder gave a
  truthful cold transfer line (175.34 kB) because repeat builds show
  BuildKit's incremental near-empty line — noted in the evidence, not hidden.
- **SIGTERM drain proven live (C6):** POST fired, SIGTERM 0.7 s later,
  uvicorn "Waiting for connections to close", the request **completed 201 at
  5.22 s** (`duration_ms=5218.9`), then `shutdown: closing connection pools`
  and clean `exit=0`. `docker stop` took 5.4 s. K8s note recorded for Ali:
  `terminationGracePeriodSeconds >= 30`.
- **E4:** compose already carries `--appendonly yes` on the named `redisdata`
  volume with the rationale comment at `compose.yaml:101-102` — ticked with a
  pointer instead of re-doing finished work.
- **4 more boxes:** C6, E4, G1, G2 (16 total ticked this session across
  M11+M12).

**Evidence:** `docs/evidence/26-backend-image-drain-aof.txt`; commits
`e6c5691` (M11 docs), `4d35bb2` (image + evidence 26).

**Next:** push the branch, open PR `Closes #5, Closes #6` (Dockerfile rides
along per Ali) → then #10 test suite (activates CI's real jobs), #17
/metrics wiring + X-Forwarded-For note for Ali, #18 docs/ADRs.

## M13 — Issue #10: test suite + CI activation (Ashar + AI agent)

**Expected:** ≥14 deterministic backend tests with coverage ≥65% and no
`time.sleep()`; activate CI's lint-and-type / test-backend / integration jobs
(their trigger is `backend/pyproject.toml`) without letting a red required
check land on `dev`.

**Achieved:**
- **`backend/tests/` — 76 tests across 14 files** (guide target 14): state
  machine (21), API behaviour incl. field-level 400s, 404/409 wording,
  pagination and `X-Request-ID` echo (9), LLM provider: malformed output not
  retried, 400 never retried, one retry on timeout/429/5xx (11), injection
  guardrail (2), rules table (9), cache MISS→HIT + duplicate-text served by
  one provider call + fallback never cached (5), redaction (5), `/ready` with
  dead Postgres and dead Redis (3), rate limit + per-client `X-Forwarded-For`
  window (2), meta+factory (3), metrics (2), JSON logging (2), seed
  idempotence (1), and the assignment's required provider-failure → 201
  `rules:fallback` (1). **Coverage 91.90%** (gate 65%); **five consecutive
  full runs, 76 passed each time, zero flakes**; no `time.sleep` anywhere
  (LLM jitter injected as `sleep=lambda s: None`).
- **CI simulated before push, not hoped for:** a throwaway venv ran CI's
  exact install sequence — `pip install -e .` fails by design (tool-only
  pyproject) → `requirements.txt` fallback fires; `pytest pytest-cov httpx`
  only, **fakeredis absent** → conftest falls back to CI's real Redis service
  container; `DATABASE_URL` without `_test` + `GITHUB_ACTIONS=true` exercises
  the CI branch of the guard, while a local run against the dev DB is refused
  (exit 2) before any fixture executes.
- **Migrate-on-boot:** the integration job does `docker compose up` on an
  *empty* database with no manual migration step — `backend/entrypoint.sh`
  now runs `alembic upgrade head` (+ idempotent seed) and `exec`s uvicorn so
  PID 1 and the SIGTERM drain stay intact; invoked via `sh` so the
  bind-mounted checkout never needs an exec bit; `.gitattributes` pins
  `*.sh` to LF (a CRLF shebang fails at container start).
- **Integration sequence executed against a real stack:** four services
  healthy on a fresh DB, X-Cache MISS→HIT, POST 201 with enum-validated
  category, GET-by-id assertion OK; torn down with `down -v`.
- ruff (new `pyproject` config: E,F,I,B,UP @ 100 columns) and mypy
  (`check_untyped_defs`) both green; OpenAPI export byte-identical.

**Evidence:** `docs/evidence/27-test-suite.txt` (gates, 5× determinism, CI-venv
simulation, guard refusal, integration summary, test inventory); commit
`75376bd`.

**Next:** push + PR `Closes #10` (stacked on PR #25) → #17 (/metrics wiring,
XFF note for Ali, F4 hit-rate script) → #18 docs/ADRs.

## M14 — Ali's blocking review answered (lifespan migration), issue #17 proven, F4 measured (2026-09-26)

**Expected:** close Ali's CHANGES_REQUESTED on PR #25 — nothing migrated a fresh
database — with exactly the lifespan `alembic upgrade head` he specified, fix the
inverted rate-limiter sentence in the PR body, keep the stacked test-suite PR
green through the Sonar gate; then finish issue #17's acceptance proof and the
F4 measurement the checklist still owed.

**Achieved:**
- **PR #25 blocking fix (`4416cd1`):** the lifespan runs `apply_migrations()`
  via `asyncio.to_thread` before serving; `alembic.ini`'s `%(here)s` plus
  env.py's environ lookup make it cwd-independent, so compose (which starts
  `uvicorn` directly), kind/CD and `scripts/k8s-up.sh` all migrate a fresh DB
  with zero infra changes. Ali's concurrency note is in the code verbatim
  (transactional DDL → losing replica aborts, restarts, retries, then no-ops
  at head). Live proof on a brand-new empty database: boot log
  `Running upgrade → 0001, initial schema` → `POST /api/complaints` 201 →
  `alembic_version=0001`, no manual alembic anywhere (evidence/25 [12]).
  The PR body's "malformed JSON is rejected before the limiter runs" claim was
  corrected — router-level `Depends` run before body parsing, so garbage **is**
  counted. `origin/dev` (#23/#24 merges) synced, **8/8 green at `4416cd1`**,
  review reply posted (comment 5848848629).
- **PR #26 synced and 8/8 green at `103ea6e` + `3521916`:** all 10 Sonar
  findings cleared (`8f8d4d5`) — S6504 by making the boot script root-owned,
  S9100 useless-yield removal, S9073 assertion splits, S1172+S7632 via bare
  `# NOSONAR` (the parenthesized rule-id syntax is rejected by the python
  analyzer), S8786 with the poss-side benchmark written into the comment;
  plus three new CI tests for #17's claims (both histograms exposed, fallback
  counter delta == 1 per degradation, `/metrics` 200 after the POST limiter
  returns 429) — **79 passed, 91.99% coverage**, ruff/mypy clean.
- **Issue #17 acceptance proven end-to-end (PR #27, evidence/28):** all five
  required series; a live always-raise provider (`SIMULATED_FAIL_MODE=raise`)
  → 201 `rules:fallback` with `triage_fallback_total` absent → 1.0 (delta
  exactly +1); the 11th/12th POST from one client → 429 while `GET /metrics`
  stays 200; Postgres stopped under a running app → `/health` 200,
  `/ready` 503, `/metrics` 200, recovery after `docker start`. The one
  behaviour change the lifespan migration brings is documented honestly: with
  an unreachable DB the app now *fails fast at boot* (uvicorn exits non-zero,
  the sanctioned abort/restart semantics) instead of serving degraded — the
  runtime-death evidence in evidence/25 [11] still stands and was re-proved.
- **F4 measured: hit_rate = 0.75** (30 hits / 10 misses / 40 lookups, expected
  (4−1)/4; two identical runs; all 40 POSTs 201; zero fallbacks) from
  `scripts/triage_hit_rate.py`, which rotates `X-Forwarded-For` so the
  per-client 10/min limiter cannot pollute the number and exits non-zero on
  any 429, split mismatch or fallback.
- **Three data boxes ticked: D1, D2, D4** (evidence/23 up/down/up + full
  schema + 34-row idempotent seed; grep proves `backend/app` contains no raw
  DDL — startup only calls `alembic upgrade head`). D3 and F4 deliberately
  left open until ENGINEERING-NOTES / TRIAGE.md carry their write-ups.

**Evidence:** `docs/evidence/25-complaints-api.txt` [12],
`docs/evidence/28-metrics-f4.txt`; PR #25 comment 5848848629; 8/8 checks on
`4416cd1` and on `3521916`'s lineage.

**Next:** PR #27 review closes issue #17 → issue #18 (TRIAGE.md carrying the
0.75 hit rate + my four ENGINEERING-NOTES answers with file:line refs) → tick
F4, D3, J5 → A3/A4 process boxes → book the demo video with Ali → dev→main.

## M15 - issue #18 docs = PR #28 (TRIAGE.md, ENGINEERING-NOTES, ADR 0001+0004) (2026-09-26)

**Expected:** issue #18's deliverables land while their `file:line` refs are
still true - TRIAGE.md (providers, JSON/Pydantic path, timeout/retry, cache +
measured hit rate, guardrail, fallback test + CI link) and my four §5.2
answers plus the "also required" extras; ADRs 0001 and 0004 per PLAN §7;
THE RULE artifacts with the milestone.

**Achieved:**
- PR #28 opened off `origin/dev` with four documents: `docs/TRIAGE.md`
  (six sections, real CI run link, reproduction command for the hit-rate
  probe), `docs/ENGINEERING-NOTES.md` (Q4 + Q8 written in full, Q7 Compose
  confirmation, Ali's Q1/Q2/Q3/Q5/Q6/Q7-write scaffolded with pending
  markers, plus the index-reasons table, stats TTL+invalidation, `redisdata`
  justification, honest "not observed live" Groq note, measured hit rate),
  `docs/adr/0001-provider-interface.md` (structural Protocol vs ABC vs
  scattered if/elif vs plugins vs framework), `docs/adr/0004-pii-and-data-
  governance.md` (per-provider egress table, what never leaves structurally).
- **106/106 `file:line` refs machine-verified** against the final-state tree
  (`feat/test-suite` content) - six wrong citations caught and fixed before
  push (test-suite's `complaint_service` is +2 vs dev, redaction's comment
  block grew, the 429 check is line 46, status-change invalidate is line 54).
  The PR body states it **must merge after #26** so every ref stays true on
  `dev`.
- All four issue-#18 topics (provider interface, retry policy, stats-cache
  TTL+invalidation, fallback guarantees) are answered somewhere in the four
  documents.
- Boxes ticked: **F7** (ADR 0004), **D3** (named-query index reasons),
  **F4** (script + 0.75 + TRIAGE §3).
- **#25 and #26 both merged into `dev` as merge commits (`3c9ee7e`,
  `1f5470b`)** with Ali's preconditions verified first (#25 landed, all 8
  checks green on #26's tip `857fdc1`, run 36265133413); this branch then
  synced with `origin/dev` and the four append conflicts (PROGRESS,
  AI-USAGE, checklist, docx) resolved by keeping both sides.

**Evidence:** PR #28 (https://github.com/AliHaiderBajwa/CivicPulse/pull/28);
`docs/evidence/28-metrics-f4.txt` (F4 hit_rate 0.75).

**Next:** Ali on #27/#28 (queue comment already posted). Then A4
commit-share recompute, README API table, RUNBOOK triage section, demo
video, dev -> main.

## M16 - #25/#26 merged per Ali's rule, CD gate exposed red, hotfix = PR #30, A4 ticked (2026-09-26)

**Expected:** execute Ali's merge instruction exactly (merge #25 first, then
sync/merge #26, merge commits never squash, watch for the ci.skip anomaly),
then keep going until every open defect is fixed.

**Achieved:**
- **#25 merged `3c9ee7e`, #26 merged `1f5470b` - both merge commits**, in
  that order; no squash, no history duplication (#26 already contained
  #25's commits). #26's preconditions were verified before merging: #25 on
  dev, all 8 checks green on the tip `857fdc1` (run 36267113413's lineage),
  no `push.pushOption ci.skip` configured. **No ci.skip anomaly**: every
  push produced a run within ~2 minutes.
- **Post-merge dev CI green** (run 36267110824) - but **dev CD went red**
  (run 36267110631): the `test (gate)` backend step ran for the first time
  in its life (its `hashFiles('backend/pyproject.toml')` guard only became
  true when #26 landed) and died on `pip install -e ".[dev]"`, which cannot
  work by design - pyproject is tool config only, and the CD copy had
  neither CI's `|| requirements.txt` fallback nor its Postgres/Redis
  services. **Issue #29** documents it; **PR #30** mirrors ci.yml's
  test-backend byte-for-byte in behaviour (services, env, install recipe,
  warm-up, coverage gate; timeout 10 -> 15 min). dev CD stays blocked
  (`needs: test`) until #30 merges.
- **docs branch (#28) synced with post-#26 dev** via merge commit
  `9e17a54`; the four append conflicts (PROGRESS M13/M14 vs M15, AI-USAGE
  rows, checklist D/F4 blocks, binary docx) resolved by keeping both sides
  + union of ticks, docx regenerated; **8/8 green**, and all **84**
  `file:line` refs re-verified against the merged tree (0 bad).
- **A4 ticked**: 87 commits on dev, Ashar 46 (52.9%) / Ali 41 (47.1%) -
  both ≥35, both ≥35%.
- Ali's non-blocking entrypoint-trim suggestion answered with the ordering
  gap it has (seed runs pre-lifespan, so deleting the alembic line breaks
  fresh-DB seeding silently) and two correct shapes (a: seed self-migrates;
  b: seed moves into the lifespan), asked which he wants.

**Evidence:** CD red run 36267110631 + green CI 36267110824 on the same
SHA; issue #29; PR #30; PR #28 checks 8/8 at `9e17a54`; `git shortlog -sn
origin/dev`.

**Next:** Ali's +1 on #30 (unblocks CD), #28, #27 → then entrypoint trim
follow-up, A1/A2/A3 evidence pass with Ali, README API table + RUNBOOK
triage section, demo video, dev -> main.

## M17 - submission gate = PR #32, RUNBOOK triage half, all four review PRs green (2026-09-27)

**Expected:** close the last gap assignable without Ali - the brief section
4/5 requirement `scripts/check_submission.py clean` - land the RUNBOOK
section that is mine, and leave every open PR green for his review.

**Achieved:**
- **`scripts/check_submission.py` (PR #32, Closes #31)** - 12 checks, one
  per automatic deduction in brief section 5: `-20` env/key history,
  `-20/-15` key patterns across tracked files, `-15` k8s base64-decoded +
  stringData with placeholder exemption, `-8` unpinned images, `-8`
  localhost service-to-service (probe/ingress-host exempt), `-8`
  frontend->DB path, `-8` published db/cache ports and non-ClusterIP
  Services, `-8` ungated publish/deploy jobs, `-8` deploying `:latest`
  (k8s/compose.prod image fields + `IMAGE_TAG=` + cd.yml's refuse-to-apply
  guard must exist), `-8` Postgres Deployment without PVC, `-5` direct
  commits to main via `git rev-list origin/main --not origin/dev`, `-5`
  quickstart file references.
- **The gate caught a real defect on its first run**: `.env.example`
  shipped `IMAGE_TAG=latest` - one `cp` away from the `-8` "deploying
  :latest" deduction. Fixed (empty + comment, so compose.prod's `:?` guard
  forces a SHA) and **mutation-tested**: the old value fails check 9 with
  the exact line, the new value passes. Ruff-clean (16 findings, incl. the
  blind-except and missing `check=False` the fix pass surfaced).
- **Publish-vs-deploy ambiguity resolved in the check**: GHCR keeps the
  brief-required `latest` *alias* (publish), while deploy is field-scanned
  (k8s `image`/`newTag`, compose.prod, `IMAGE_TAG=`, guard presence) so
  cd.yml's own `grep ':latest'` refusal and the explanatory comments do
  not self-flag.
- **`docs/RUNBOOK.md` (my half of #14)** landed as `8f40adb`: the complete
  triage-failing section - diagnostics, error-class table, safe actions for
  compose + k8s, `FLUSHDB` notes, always-raise drill, fail-fast caveat;
  Ali's deploy/rollback/logs sections scaffolded pending.
- **Review surface all green**: #27 8/8, #28 8/8 (at `8f40adb`), #30 8/8
  (at `238e12c`). #30's Sonar sweep: S6698 cleared on both credential
  literals with justified bare `# NOSONAR` (ephemeral service credential,
  identical to ci.yml - `POSTGRES_PASSWORD` needed one line, `DATABASE_URL`
  its own); S8541/S8544 cleared by installing from `requirements.lock`
  (`--only-binary :all: --no-deps --require-hashes`, the Dockerfile's own
  recipe) plus pinned `pytest==9.1.1 pytest-cov==7.1.0 httpx==0.28.1` -
  test-backend green on the pins.
- Checklist box **`python3 scripts/check_submission.py` clean** ticked.

**Evidence:** PR #32 (Closes #31); gate run 12/12 PASS exit 0;
`ruff check scripts/check_submission.py` clean; mutation run FAIL at
`.env.example:21`; PR #30 checks 8/8 at `238e12c`.

**Next:** Ali's reviews on #27/#28/#30/#32 (all green) -> merges in order
(#30 first: unblocks dev CD) -> entrypoint trim per his a/b pick ->
A1/A2/A3 evidence pass -> README quickstart staleness (lines 13-15 still
describe the pre-#25 stub path - his file) -> demo video -> dev -> main.

## M18 - Wave 1 complete: all four PRs merged in Ali's order, CD proven green (2026-09-27)

**Expected:** execute Ali's review wave exactly as he ordered (#30 first, #27
before #28, #32 last), prove the CD hotfix live for him in-thread, and start
the process-evidence pass while he writes Wave 2.

**Achieved:**
- **All four approvals landed from Ali**: #30 (he owned the missing-fallback
  root cause as his bug in-thread), #27, #28 *conditional on merging #27
  first* (the F4 tick points at #27's files — he flipped my listed order with
  reasoning in the review), #32 (he ran the gate himself: 12/12 clean).
- **Merged in his order, all merge commits**: #30 `b356d40` → #27 `226bf3f`
  → #28 `792298b` → #32 `f40a3ab`. Issues **#17/#18/#29/#31 auto-closed**;
  open PRs = 0; only #14 remains open (his docs halves).
- **CD hotfix proven live**: run **36306336956 completed SUCCESS** on
  `b356d40` — the `test (gate)` backend step that was red yesterday went
  green on its first post-merge execution; Ali watched per his request and
  the in-thread comment carries the link. Intermediate runs for `226bf3f`/
  `792298b` were auto-cancelled by newer pushes; the final-state run
  **36306517542** on `f40a3ab` is the submission-pack link.
- **Entrypoint ruling on #26: keep as-is, retraction posted** — the ordering
  gap analysis stood, he agreed, no follow-up PR needed.
- **J4 shot list + two recording slots published as issue #33** (assigned to
  Ali, awaiting his pick; open question flagged: recording tool).
- **`docs/evidence/29-a2-a3-process.txt`**: A2 proof (main = 3 Block-0
  bootstrap commits, `rev-list origin/main --not origin/dev` = 0, gate check
  11 runs the same command) + A3 inventory (**10 qualifying PRs** vs the 5
  required, verbatim substantive review quotes from both partners). A2/A3
  ticked with pointer — Ali's review of this PR is the confirmation; A1
  still needs his screenshot.
- A4 recompute noted in the evidence: 103 dev commits = 62/41 → 60.2%/39.8%,
  still both ≥35.

**Evidence:** `docs/evidence/29-a2-a3-process.txt`; CD run 36306336956
(success); merged SHAs above; issue #33.

**Next:** Ali's Wave 2 (J5 answers, ADR 0002+0003, J3 RUNBOOK halves, J1
README, A1 screenshot, BN decision) → my pack assembly as his PRs land →
video on his slot → dev → main.

## M19 — Wave 2 docs: J5/J2/J3/J1/A1, closes #14 (2026-09-27)

**Expected:** Ashar's queue items 2+3 — one docs PR off settled dev with my
six ENGINEERING-NOTES answers, two ADRs, three RUNBOOK sections, README
refresh, and the A1 branch-protection shot.

**Achieved:**
- **J5:** Q1 (3 laptop-vs-CI differences, all line-anchored), Q2 (ladder
  position + next rung, no slide quotes), Q3 (cd.yml:293 + :296-303 guard),
  Q5 (71 s scale-up lag decomposed: metrics pipeline dominant, policy
  windows cited, flapping blip explained), Q6 (VPA Off + the Auto fight),
  Q7 K8s side (no NetworkPolicies — stated as an honest gap + closer),
  pgdata/ollama_models justifications, build-context interpretation,
  Groq no-live-observation confirmation. Zero `_Pending_` remain.
- **J2:** ADR 0002 (envsubst runtime injection, verified nginx.conf +
  Dockerfile lines) + ADR 0003 (deploy-by-SHA, verified cd.yml lines).
- **J3:** deploy (compose/k8s-up/CD), rollback (undo vs SHA re-apply +
  migrations-only-forward rule), logs (incl. --previous + request_id).
- **J1:** quickstart is the plain one-command form (Dockerfile exists;
  stub footnoted), CI/CD badges, screenshots 31 (dashboard, live k3d row)
  + 32 (submit form) captured in-browser against the live stack.
- **A1:** evidence/30 rendered from the live branch-protection API (PR +
  1 approval + 7 checks + no force/deletion). Browser shots are real
  viewport captures; API renders are exact-output renders (method as
  disclosed for evidence 02-04).

**Evidence:** this PR (closes #14); checklist J1/J2/J3/J5/A1 ticked with
pointers; screenshots + API render committed.

**Next:** Ashar reviews/merges per Wave 3 (ticks already in this PR);
BN call + video slot reply posted; J4 video at the booked slot.


## M20 — frontend redesign: civic-ops design system, zero test changes (2026-09-27)

**Expected:** user asked for a premium frontend via the frontend skill.
Delegation to a visual-engineering subagent failed twice (API outage, then
insufficient account funds), so the work moved in-house following the same
skill protocol: ui-ux-pro-max design-system direction + redesign-skill
audit-first workflow + DESIGN.md contract before components.

**Achieved:** DESIGN.md contract; index.css token system; App/Submit/
Dashboard/Stats refined with every test hook preserved (15/15 green, zero
test edits at the time); tsc/eslint/build clean; screenshots re-captured
live. Full detail in M20b below; history rewritten once to drop an
accidental Wave-2 contamination (branch rebased clean, force-pushed).

## M20b — Stitch-fidelity pass: reference-matched UI, honest omissions (2026-09-27)

**Trigger:** user-supplied Stitch screens + shield logo as visual contract;
taste-skill design read (VARIANCE 4 / MOTION 3 / DENSITY 5, Inter correct
for accessibility-first briefs). Adapted, not cloned: ~20 unbacked controls
omitted as theatre (logged in DESIGN.md); icon font replaced by inline SVG;
WCAG AAA footer claim refused.

**Achieved:** Inter scale, 80rem container, joined tab container, hero
action rows, record pill, numbered pagination (+1 test: 16/16 green),
result meta grid (real fields only), stat icons + computed shares, favicon.
tsc/eslint/build clean; re-captured live. Zero backend/k8s/contract/infra
changes.

## M21 — BN1: zero-downtime rolling update proven under live load (2026-09-27)

**Expected:** rubric BN1 (+4) — replace every backend pod mid-load with zero
failed requests, on the unmodified deployment strategy.

**Achieved:**
- New probe `scripts/load/rolling-update.js`: constant 15-VU load (POST +
  GET per iteration, unique XFF per request, ingress Host routing) for
  150 s; `kubectl rollout restart deployment/backend` fired at T+50 s and
  completed during the run (rollout history advanced).
- Result: **0 failed requests out of 12,068 checks (100%)**, 6034
  iterations, 0 interrupted. No manifest changes were needed — strategy was
  already `RollingUpdate` with `maxUnavailable: 0`; HPA stayed on.
- Honest scope in evidence/34: k3d image under test was the `:dev` stub
  build (platform-mechanics proof, app-agnostic); cited numbers are k6's
  canonical text summary, quoted verbatim.

**Evidence:** docs/evidence/34-bn1-zero-downtime.txt; scripts/load/rolling-update.js.

<!-- New entries above this line. -->
