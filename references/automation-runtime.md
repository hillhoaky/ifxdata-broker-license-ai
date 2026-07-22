# Automation runtime

Use this reference before creating scheduled, unattended, or batch executions of the IFXData broker license scoring workflow.

## Recommended execution model

The best long-term design is:

```text
Codex automation
  -> IFXData admin API
  -> official website precheck
  -> Gemini Web
  -> local deterministic parser
  -> IFXData admin API write-back
```

In this model, routine scoring does not depend on DeepSeek or IFXData screen scraping. Codex remains responsible for orchestration, official-website comparison, Gemini Web scoring, local parsing, exception handling, and final verification.

DeepSeek may be added only for optional translation, exception review, or batch summaries. If used in production, route DeepSeek through an IFXData backend proxy so Codex never stores or transmits the raw DeepSeek key.

## Required unattended runtime configuration

An unattended run may start only when all items are true:

- Gemini API is configured and available, or Gemini Web is signed in and the user has approved web fallback.
- IFXData Global broker and license read/write access is available through confirmed APIs.
- The broker Global `Web link` can be read, or a missing/unavailable website can be recorded without blocking the scoring run.
- The run has a finite broker scope, batch size, or time budget.
- A cursor/result file path is available for resume.

If Gemini or IFXData API access requires a human approval click during the run, return `blocked_runtime_authorization_required` or the more specific blocked status and do not start a scheduled unattended run. DeepSeek access is optional and should be skipped when unavailable.

## Suggested batch policy

- Default batch size: 1 broker or 10 licenses per run during early rollout.
- Default cadence: every 30 minutes only after one supervised batch completes without blocked states.
- Run IFXData reads/writes through confirmed APIs. Do not use browser DOM/screenshot extraction in scheduled runs.
- Retry local parser only by asking Gemini once again with the same template when the answer is malformed.
- Run official-website precheck once per broker before the first Gemini prompt. If material differences are found, pause before scoring and ask the user to correct IFXData or explicitly continue.
- Do not retry authentication, quota, network-authorization, or permission errors in a loop.
- Skip records already verified `completed` unless refresh is explicitly requested.
- Save a result row after every license, not only at batch end.
- Gemini API scoring must be sequential by default: one broker at a time per worker, no parallel license scoring, target no more than 3 requests per minute per Codex worker when CodexA/CodexB share the same Gemini key/project, wait at least 20 seconds between licenses, pause at least 60 seconds between brokers, keep a daily safety cap of about 1,000 Gemini scoring calls per API key unless a higher active AI Studio limit is confirmed, retry HTTP 429 with 60-second then 120-second backoff, then stop with `gemini_rate_limited`.
- Use `scripts/gemini_license_api.py` for Gemini API scoring because it includes a local shared rate-limit file (`GEMINI_RATE_LIMIT_FILE`) that coordinates same-machine Codex sessions. If workers run on different machines, use separate Gemini keys/projects or a central IFXData-owned queue for true cross-machine throttling.

## Production hardening

For optional DeepSeek production use, implement IFXData backend endpoints such as:

```text
POST /internal/license-ai-score/preflight
POST /internal/license-ai-score/parse
POST /internal/license-ai-score/report
```

The backend should:

- Accept already-redacted payloads where possible.
- Store no secrets in request/response logs.
- Enforce per-run and per-day cost limits.
- Return structured `ready`, `valid`, `needs_review`, or `blocked` statuses.
- Include token usage and model metadata.
- Keep mappings between private IFXData values and placeholders local to IFXData systems.

Codex should continue to validate that no private values are sent outside the approved boundary. Routine parsing should remain local.

## Human supervision triggers

Pause the run and ask for review when:

- Gemini or DeepSeek reports identity mismatch, clone risk, revoked/suspended license, or unverifiable license number.
- The official website shows a materially different legal entity, license number, license scope, or extra/missing license compared with IFXData Global.
- Existing Score or AI Score Introduction is non-empty and no overwrite was authorized.
- The IFXData write contract or Global scope cannot be confirmed.
- Browser login, CAPTCHA, network approval, or manual permission is required.
- A save succeeds but read-after-write verification fails.
