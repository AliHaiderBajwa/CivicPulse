# ADR 0004: PII and data governance for the AI layer

- **Status:** Accepted, 2026-09-26
- **Authors:** Ashar Ahmed (with opencode, disclosed in `docs/AI-USAGE.md`)
- **Context:** CS4032 Assignment 1 brief §4 — "what leaves your machine, to whom,
  and why it's acceptable".

## Context

Citizens submit complaint text (which may contain emails, phone numbers,
national IDs) and an optional `reporter_contact` for follow-up. One of the
four triage providers (`TRIAGE_PROVIDER=llm`) is a hosted LLM (Groq). The
assignment requires a hard answer on what is sent off-box and why that is
acceptable.

## Decision

**Only redacted complaint text may ever reach a provider, and only when a
hosted provider is explicitly configured.**

1. **Redaction is applied before egress, not after.** The orchestrator
   redacts first and only ever hands the redacted string to a provider:
   `safe = redact(text)` at
   `backend/app/services/triage_orchestrator.py:42`, then
   `self._primary.triage(safe, location)` at `:61`. The patterns live in
   `backend/app/services/redaction.py:9-11`: emails → `[email]`, CNIC
   numbers → `[id]` (checked before the phone rule because a 13-digit CNIC
   would otherwise match it), phone numbers → `[phone]`.
2. **What leaves the machine, per provider:**

   | `TRIAGE_PROVIDER` | Egress | Payload |
   |---|---|---|
   | `rules` (default) | none | — |
   | `simulated` | none | — |
   | `ollama` | local `ollama:11434` only (`config.py:19`) | redacted text; stays on the host |
   | `llm` | `https://api.groq.com/openai/v1` (`config.py:16`) | redacted text + static system prompt (`llm.py:60-66`) |

3. **What never leaves, structurally:**
   - `reporter_contact` is never passed to the triage layer at all — it goes
     from the request straight to the repository
     (`complaint_service.py:21` calls `triage.run(data.text, data.location)`;
     `reporter_contact` is only bound at `:23`).
   - The unredacted original text stays in Postgres only; Postgres/Redis sit
     on `internal: true` networks with no published ports
     (`compose.yaml:145-146`, k8s Services are cluster-internal).
   - `LLM_API_KEY` is a `SecretStr` (`config.py:15`) — it never appears in
     `repr`, logs or error bodies; it arrives from the environment (GitHub
     Secrets in CI/CD, ConfigMap/Secret in k8s).
   - Request logs are structured metadata only (`request_id`, method, path,
     status, duration — `backend/app/middleware.py`); the fallback WARNING
     carries `complaint_id`/`provider`/`error_class`, not text
      (`complaint_service.py:31-35`). The outcome ring pushed to Redis stores
      provider/latency/fallback flags only (`triage_orchestrator.py:84-87`).
4. **Purpose limitation:** the egressed text exists to classify one
   complaint (category/priority/summary ≤140 chars) and nothing else; the
   response is stored in our own database, not used for training or retained
   by us at the provider beyond its API processing.

## Why this is acceptable

- **Minimal and transformed:** a third party receives a *redacted* derivative
  of one field (complaint text), never contact details, never the database.
- **Default-deny:** the default configuration (`rules`) sends nothing
  anywhere; hosted egress requires an explicit environment choice.
- **Bounded:** one HTTP call per uncached complaint, 10 s timeout
  (`config.py:21`), content-hash cached for 24 h (`config.py:24`) so
  identical text is not re-sent on every submission.
- **Reviewable:** the egress surface is one call site
  (`triage_orchestrator.py:61`) — grepping for provider calls finds it, and
  `backend/tests/test_redaction.py` pins the redaction behaviour.

## Consequences

- PII that citizens put in complaint text is stripped before any provider
  sees it; PII in `reporter_contact` never reaches the AI layer at all.
- Redaction is a code-enforced invariant rather than a prompt instruction —
  the model is never asked to "ignore" PII, it simply never receives it.
- If a fifth provider is added, it must consume the same redacted `safe`
  string; extending `TriageProvider` (`base.py:19-22`) does not bypass the
  orchestrator's redaction step.
