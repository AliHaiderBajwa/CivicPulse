# AGENTS.md — standing orders for any AI session in this repo

**Project:** CivicPulse — CS4032 Software Construction and Design, Assignment 1.
**Plan of record:** `docs/PLAN.md` (copy of the audited 48-hour partner plan).
**Roles:** Ali Haider Bajwa (this machine, gh = `AliHaiderBajwa`) owns frontend, Compose, Kubernetes, CI/CD, evidence. Ashar owns backend, data, Redis, AI layer. AI agent (opencode) pair-programs with Ali and must disclose its work in `docs/AI-USAGE.md`.

## THE RULE (do not forget, never skip)

After **every** milestone / completed checkbox batch, before starting anything new:

1. Append a `PROGRESS.md` entry: expected → achieved → evidence → next.
2. Regenerate the docx: `python3 scripts/build_docx.py`.
3. Tick the matching boxes in `docs/RUBRIC-CHECKLIST.md`.

A milestone is **not done** until code is committed AND all three artifacts are updated.

## Hard rules (automatic deductions)

- NEVER commit `.env`, keys, tokens, passwords. `.env` is gitignored; secrets go to GitHub Secrets / K8s Secret placeholders only. If leaked: rotate + incident note (−20).
- NEVER deploy `:latest`. Deploy by commit SHA (`${{ github.sha }}`).
- NEVER use `localhost` for service-to-service calls — Docker/K8s DNS names only (`backend`, `database`, `cache`).
- ALWAYS pin base images by tag (`python:3.12-slim`, `postgres:16-alpine`, `redis:7-alpine`, `node:22-alpine`, `nginx:1.27-alpine`).
- Postgres = StatefulSet + PVC, never a Deployment. No published DB/cache ports anywhere.
- `needs:` gates every publishing/deploying CI job.
- No direct commits to `main` — everything lands via PR into `dev`, then `dev` → `main`.

## Git conventions

- Branches: `feat/...`, `fix/...`, `docs/...`, `ci/...` off `dev`; PRs into `dev`; partner reviews within 15 minutes.
- Commits: conventional prefixes (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`), small, ≥35 total, neither partner < 35%.
- Every PR body includes `Closes #N`.

## Key commands

```bash
python3 scripts/build_docx.py        # regenerate docs/CivicPulse-Documentation.docx
python3 scripts/check_submission.py  # pre-submission lint
docker compose up -d --wait           # local system (dev)
pytest --cov=app backend/tests        # backend suite (backend/ cwd: pytest)
cd frontend && npm test               # vitest
```

## Priority when behind (PDF's own advice)

AI layer (F) > backend (C) > CI/CD (I) > Kubernetes (H). Never skip the fallback test:
*provider that always raises → POST /api/complaints still returns 201 with `triaged_by == "rules:fallback"`.*
