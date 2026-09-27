# ADR 0001: The TriageProvider structural interface

- **Status:** Accepted, 2026-09-25
- **Authors:** Ashar Ahmed (with opencode, disclosed in `docs/AI-USAGE.md`)
- **Context:** CS4032 Assignment 1 brief — four triage implementations
  selectable by environment variable (rubric F1).

## Context

Triage must be implementable four different ways — a hosted LLM (Groq), a
local LLM (Ollama), a deterministic keyword engine, and a deterministic CI
fake — and selected at runtime by one environment variable
(`TRIAGE_PROVIDER`, `backend/app/config.py:14`). The orchestrator must treat
them identically, CI must run the suite with zero network and zero wall-clock
flakiness, and reviewers must be able to add a fifth provider without reading
the whole service.

## Decision

**A structural `Protocol` at the seam, one frozen result model, and exactly
one selection point.**

1. The interface is a `typing.Protocol`
   (`backend/app/providers/triage/base.py:19-22`):

   ```python
   class TriageProvider(Protocol):
       name: str
       def triage(self, text: str, location: str) -> TriageResult: ...
   ```

   Nothing inherits from it. A provider satisfies it by *shape* — any class
   with a `name` and that method works, including hand-written test doubles.
2. Everything a provider returns crosses one shared contract,
   `TriageResult` (`base.py:8-12`): enum `category`/`priority`, bounded
   `summary`, bounded `confidence`. Rules and the LLM return the same type,
   so the fallback's output is schema-identical to the primary's.
3. Selection happens once, in `build_provider()`
   (`backend/app/providers/triage/factory.py:11-28`), driven by the
   `Literal` on `Settings.triage_provider` (`config.py:14`). The
   orchestrator receives already-constructed objects via constructor
   injection and imports only `base` — never a concrete class
   (`triage_orchestrator.py:9`).

## Alternatives considered

- **Abstract base class + inheritance.** Familiar, but couples every
  implementation to one Python class hierarchy, forces `isinstance` checks
  and registration, and makes `tests/doubles.py` import production code just
  to fake it. Structural typing gives the same static guarantee with less
  coupling.
- **`if/elif` at the call sites.** Would work at four providers, but the
  branch would be duplicated wherever a provider is constructed (app wiring,
  tests, scripts) and drift between them. One factory is one place to review.
- **Dynamic plugin loading (entry points / `importlib`).** Flexible for a
  real plugin ecosystem; here it hides the dependency list from reviewers,
  weakens `mypy`'s reach, and buys nothing when the set of providers is
  known and closed.
- **A framework abstraction (e.g. an LLM-chain library).** Adds a heavy
  dependency and build-context cost for one method call; the assignment's
  seam is a single method, not a chain.

## Consequences

- Adding a provider = one class + one `elif` in the factory + one value in
  the `Literal` (`config.py:14`). The orchestrator, cache, fallback path,
  stats and routes are untouched — the interface pays for itself at the
  second provider and compounds after that.
- CI runs the entire suite offline: doubles that satisfy the protocol
  without importing it (`tests/doubles.py`), plus
  `TRIAGE_PROVIDER: simulated` in the workflow
  (`.github/workflows/ci.yml:77`). No API keys, no flakiness.
- Because `TriageResult` is one model, "always-raise provider → rules
  fallback" tests compare fields, not formats
  (`backend/tests/test_fallback.py:7-14`).
- The seam is also the security boundary: the orchestrator redacts before
  calling the interface, so *every* implementation receives already-redacted
  text by construction (see ADR 0004) — a new provider cannot be handed raw
  citizen text without changing the orchestrator itself.
- Cost accepted: a structural match is only checked statically (mypy in
  `lint-and-type`) or at first call, not by inheritance at class-definition
  time. With mypy gating CI, a shape mismatch fails the PR, not the demo.
