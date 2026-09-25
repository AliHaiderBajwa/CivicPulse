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

<!-- New entries above this line. -->
