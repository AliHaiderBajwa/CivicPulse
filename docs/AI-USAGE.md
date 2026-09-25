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
| M5 k8s | `k8s/` base + overlays manifests | Validated with kubeconform (16/16); Ali reviewed probe/resource rationale |

## Rules the AI agent worked under

- Never writes real secrets (`.env` is gitignored; K8s Secret = placeholders).
- Never commits `.env` or pushes to `main` directly.
- Every AI-authored commit uses the same conventional-commit style as the
  human partners and is pushed only through `dev`.
- The AI agent does not author partner-review approvals — reviews are human.
