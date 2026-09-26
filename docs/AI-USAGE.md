# AI-USAGE.md — disclosure of AI-assisted work (required by the assignment)

Per the assignment, AI tools were used to pair-program with the human authors.
All AI output was written, reviewed, and committed by the human partners, who
remain responsible for every line.

## Tooling

- **opencode (Claude Sonnet / Anthropic models)** — primary pair-programming
  agent, working on Ali's machine inside the repo.

## What the AI agent did (by milestone)

| Milestone | Work | Human oversight |
|---|---|---|
| M0 docs | Extracted the PDF into `docs/ASSIGNMENT-BRIEF.md`, audited the 48h plan (gaps G1–G7 amended), wrote `AGENTS.md`, `PROGRESS.md`, rubric checklist, docx builder | Ali reviewed and approved every file before commit |
| M1 Block 0 | `docs/openapi.json` contract, stub backend, 14 GitHub issues, branch protection, README | Ali verified routes against PDF §2.2 line by line |
| M2 frontend | React/Vite/TS app, typed client, 15 Vitest tests, Dockerfile, nginx.conf | Ali (and a second independent agent pass) ran tsc/eslint/vitest/build gates |
| M3 compose | Two-network compose stack, volumes, healthchecks, segmentation proof | Ali ran the stack and inspected the `ping database` evidence |
| M4 CI | `.github/workflows/ci.yml` (7 jobs), red→green fixes, required checks | Ali watched every run; fix commits reviewed before push |
| M5 k8s | `k8s/` base + overlays, VPA recommender install, k3d bring-up, stub contract completion, k6 load scripts + HPA/VPA evidence | kubeconform 16/16 in CI; probes/resources dumped from the live cluster; chart inspected before commit; two load-test bugs diagnosed from raw k6 JSON |

## Rules the AI agent worked under

- Never writes real secrets (`.env` is gitignored; K8s Secret = placeholders).
- Never commits `.env` or pushes to `main` directly.
- Every AI-authored commit uses the same conventional-commit style as the
  human partners and is pushed only through `dev`.
- The AI agent does not author partner-review approvals — reviews are human.
| M6 cd | `.github/workflows/cd.yml` (build→publish→deploy-k8s), vendored VPA CRD + recommender, `scripts/cd-evidence.sh` | Four defects found by actually running the pipeline (unbound `env` twice, missing VPA CRD, `needs` scoping) — each reproduced in a red run before the fix; actionlint added as a pre-push gate; the real Groq key was never sent to GitHub (placeholder secret only) |
| M7 release | `release.yml` (semver tags, notes, SBOM), `cd.yml` reshaped to `test→build→publish→deploy-k8s` with SBOM + digests, deploy-by-SHA guard, persistence + release-surface evidence, handoff correction | An AI-authored handoff claim was found to be **false** (compose does not auto-switch to `backend/`) and corrected rather than left to mislead the partner; the persistence proof's first capture deleted no pods and "passed" vacuously, so it was thrown out and redone; a guard the agent wrote was over-broad and turned a live pipeline red, which is how the real defect surfaced |
| M8 A5 conflict | Ashar's PR #20 reviewed/merged; Ali's conflicting branch from pre-merge base; real markers captured; resolved to 5s; evidence PNGs rendered from byte-exact captures; PR #21 opened for Ashar's review | The agent verified Ashar's 5s claim against the file before approving (db/cache both 5s) rather than rubber-stamping; the PNG method is disclosed, not passed off as screenshots; A5 deliberately left unticked until the partner's review lands |
