---
name: ifxdata-broker-license-ai-score
description: Precheck a broker's official website disclosures against IFXData Global license records, score individual broker licenses with QuickRouter Gemini API, Google AI Studio Gemini API, or Gemini Web fallback, optionally enrich missing country/begin-date/email/telephone fields from concrete Gemini findings, parse and validate Gemini answers locally by deterministic script, and update confirmed fields through IFXData admin APIs. Use for API-first single-broker tests, broker-list batches, resumable processing, verified Global license updates, and optional DeepSeek translation/exception summaries.
---

# IFXData Broker License AI Score

## Hard rules

- Start from `https://admin.ifxdata.com/dashboard/broker-new?page={page}` and process only the broker(s) requested by the user.
- Read and write only the `Global` license record. Do not update other language tabs; they inherit from Global.
- Before license scoring, get the broker's `Web link` from the broker Global page and run an official-website precheck against the Global license records.
- Treat the official-website precheck as a separate first stage. Confirm whether IFXData has extra/missing licenses before any Gemini scoring. If license count, entity, number, scope, or material identity fields differ, stop and give the user a correction list; resume scoring only after the user says the backend has been corrected or explicitly authorizes continuing.
- If the user explicitly says `你去修改`, `帮我修改`, `可以直接改`, or an equivalent authorization for the current broker, Codex may correct confirmed IFXData Global license base fields through the API before scoring. Allowed precheck-correction fields are `type`, `no`, `beginTime`, `status`, `company`, `fullName`, `country`, `email`, `telphone`, and `address`. Do not change `key`, `licenseId`, `image`, add/delete licenses, or overwrite non-empty `score`/`ai` under this authorization. Always show the planned corrections, write through the strict `updateLicense` whitelist, and verify with a fresh API read before asking Gemini.
- If the official website discloses missing licenses and the user authorizes Codex to add them, stage an add-license draft first. Add only missing license records that are supported by official website/regulator evidence, use existing IFXData license-type options, split multi-activity SFC records into one license row per activity type, and verify every added record by API read before Gemini scoring.
- When correcting `type`, do not invent free-form license-type text. Read `license-type-standardization.md`, then choose the closest existing IFXData `Type of license` option from `broker/getAllLicenseType?language=en`. If no close option exists and the user has authorized license-type maintenance, create a new English license type with `name`, `licenseType`, `typeRange`, `note`, `language: "en"`, and `color: "Black"`, then verify it appears in the list before using it. Known mappings: FinCEN/MSB registrations use `Money Services Business`; crypto exchange or virtual-asset registrations use `Virtual asset service provider`.
- Use IFXData admin APIs for broker lookup, Global broker detail/Web link, Global license enumeration, existing-value checks, saves, and read-after-write verification after the exact authenticated endpoints and payloads are confirmed. For existing license edits, use `POST /api/v1/admin/broker/updateLicense`. Use `POST /api/v1/admin/broker/addLicenseToBroker` only for adding licenses or confirmed full-list saves. Keep credentials in environment variables or an untracked local `.env.local`, never in tracked skill files or logs. Use browser UI only for endpoint discovery, Gemini Web, and official website pages. Do not use browser UI to write IFXData records unless the user explicitly says `允许 UI fallback` or `允许网页回填` for that run.
- Do not use screenshots or broad DOM dumps as the primary method for IFXData data extraction. Routine IFXData reads/writes must be API-first to control token usage and reduce UI fragility.
- Before any broker scoring run, perform a lightweight IFXData API health check against the confirmed license/list endpoint. If the API is unreachable, credentials are missing, DNS fails, or write access cannot be verified, stop before Gemini scoring or write-back and report `api_unavailable`. Do not silently continue with browser UI fallback.
- Treat each license as an independent record. Process licenses in their displayed order unless the user names a specific license.
- Prefer QuickRouter Gemini API for license scoring when `QUICKROUTER_API_KEY` is configured. Otherwise use Google AI Studio Gemini API when `GEMINI_API_KEY` or `GOOGLE_AI_STUDIO_API_KEY` is configured. Use `scripts/gemini_license_api.py` with `gemini-2.5-flash`; for Google AI Studio direct calls set `thinkingBudget: 0`. Use the signed-in Google Gemini web app at `https://gemini.google.com/app` only as fallback when the API is unavailable or the user explicitly asks for web Gemini.
- Use local deterministic parsing and validation for routine Gemini answers. Do not require DeepSeek for normal scoring, parsing, validation, or write-back.
- When IFXData license fields such as country, begin time of licence, email, telephone, or address are empty, ask Gemini for optional supplemental values during the scoring prompt. Fill only concrete values into empty fields; leave unresolved fields blank. Do not overwrite non-empty IFXData fields from Gemini supplemental output unless the user explicitly corrected/authorized that field.
- Do not run broad secondary research for every Gemini result. Trigger secondary verification only when Gemini's `license_information_accuracy`, introduction, or supplemental evidence raises a material concern such as `cannot verify`, `identity mismatch`, `company mismatch`, `number mismatch`, `license number appears to be a company registration number`, `not a traditional financial license`, `scope unclear`, `generic contact details`, or similar uncertainty. For a triggered license, check official broker/regulator/company-register sources, update the prompt with the new evidence, ask Gemini once again, and proceed only if the concern is resolved or clearly narrowed. If it remains unresolved, stop that license as `needs_review`.
- Use DeepSeek as the default supporting layer for non-scoring language/structure tasks when `DEEPSEEK_API_KEY` is available: official-disclosure structuring, website-vs-backend difference summaries, license-type suggestions, English compression/translation, Chinese batch reports, and exception review. Do not use DeepSeek for final license scoring, API write decisions, or regulator fact verification. Redact private IFXData values unless the text is already public official website/regulator disclosure authorized for processing.
- Preserve Gemini's substantive English assessment. Remove interface noise and duplicated prompt text, but do not invent, translate, or materially rewrite its reasoning.
- Accept only one explicit integer score from 0 through 100. Never infer a score from tone, category subscores, dates, or license numbers.
- Match a result to the source license using broker ID plus license record ID when available; otherwise require the normalized tuple `(institution, license number, company registration name)`.
- Never overwrite an existing non-empty score without explicit user authorization. Record the old value before an authorized overwrite.
- Do not save partial or ambiguous data. If Gemini is blocked, returns no valid score, or the license identity is uncertain, stop that license and report the issue.
- If Gemini returns HTTP 429 or repeated provider errors during a broker run, stop new Gemini requests for that broker after the configured retry/backoff. Write only already-valid parsed results, mark unresolved licenses `gemini_rate_limited`, and resume later.
- If an IFXData write or verify request times out, do not repeat the write immediately. First perform a fresh API read for the same record(s); treat the write as successful only when read-back verifies the exact target fields.
- Never expose credentials, session cookies, tokens, or secrets.

## Required references

- Read [references/gemini-license-score-prompt.md](references/gemini-license-score-prompt.md) before asking Gemini. Prefer `scripts/gemini_license_api.py` for API scoring.
- Read [references/gemini-api-provider.md](references/gemini-api-provider.md) before using Gemini API, batching Gemini calls, or changing model/rate-limit settings.
- Read [references/local-parser.md](references/local-parser.md) before parsing Gemini answers or staging updates.
- Read [references/official-website-precheck.md](references/official-website-precheck.md) before querying Gemini for any broker.
- Read [references/license-type-standardization.md](references/license-type-standardization.md) before comparing or correcting license `type` values, and before creating any new license type.
- Read [references/data-fields.md](references/data-fields.md) before building an update record or payload.
- Read [references/ifxdata-admin-api.md](references/ifxdata-admin-api.md) before reading or writing IFXData license records.
- Load [references/ifxdata-api-mapping.json](references/ifxdata-api-mapping.json) before API-first broker runs and resolve any `unconfirmed` fields before unattended write-back.
- Read [references/api-first-implementation.md](references/api-first-implementation.md) before implementing, batching, or optimizing IFXData access. Use `scripts/ifxdata_api_health_check.py` for the required pre-run API health check.
- Read [references/automation-workflow.json](references/automation-workflow.json) before batch execution, resuming a run, or implementing orchestration.
- Read [references/automation-runtime.md](references/automation-runtime.md) before creating scheduled, unattended, or batch automation.
- Read [references/deepseek-pipeline.md](references/deepseek-pipeline.md) before disclosure structuring, type suggestions, translation/compression, reporting, or exception-review stages.

## Workflow

1. Load the confirmed IFXData endpoint mapping. If it is missing, run one supervised endpoint-discovery pass from `api-first-implementation.md` before batch work; do not repeatedly operate from screenshots/DOM for normal runs.
1a. Run the API health check from `api-first-implementation.md`. If it fails, stop the broker run before Gemini scoring and report the API failure reason unless the user has explicitly authorized UI fallback for this exact run.
2. Resolve the exact broker through the broker list/detail API. Capture broker name, broker ID, and Global context from API response.
3. From the broker Global detail API, capture the `Web link` official website URL. This is the same Global-page Web link source used by the broker AI score workflow.
4. Read the broker's `Global` license records through the confirmed Global license API.
5. Enumerate all license records in API/display order. Capture the source fields defined in `data-fields.md`, including the stable license record ID.
6. Stage 1 — run the official-website precheck from `official-website-precheck.md`. Compare website-disclosed regulators, legal entities, license numbers, and scopes with IFXData Global license records before scoring:
   - If the official website cannot be opened, continue with current IFXData Global license data and record `website_unavailable`.
   - If the official website shows mismatched company names, license numbers, scopes, or missing/extra licenses, use DeepSeek to structure/summarize the public disclosure or redacted difference list when available, then stop before Gemini scoring and report the differences so the user can correct IFXData first.
   - If the user says the backend has been corrected, perform a fresh API read before scoring.
   - If the user explicitly authorizes Codex to make corrections, apply only confirmed base-field corrections through `updateLicense`, verify by API read, then restart the comparison/scoring stage from fresh backend data.
   - If the user explicitly authorizes continuing despite differences, keep the affected licenses marked for careful review.
7. Run local source checks before querying Gemini. Confirm institution, license type, license number, status, and company registration name are present. Apply known local special rules:
   - Require institution, license type, license number, status, and company registration name.
   - CIRO exception: CIRO supervises firms through Dealer Member status and may not provide an FCA-style standalone license number. For a CIRO Investment Dealer Member, accept `Not applicable — CIRO Dealer Member` as the license-number value and match the record using institution, membership type, exact legal entity, status, and address.
   - Keep an unavailable start date or address as `Not provided`; do not invent it.
   - Flag duplicate license numbers, missing legal entities, or ambiguous identity for review.
8. Stage 2 — ask Gemini only after Stage 1 is matched, website unavailable, user corrected, or user authorized continuing. Prefer Gemini API through `scripts/gemini_license_api.py`. Use one Gemini request for 1-3 total eligible licenses when practical; when a broker has 4 or more eligible licenses, split into groups of 2 licenses per Gemini request. Do not put more than 3 licenses in one API request unless the user explicitly asks and rate/quality risk is acceptable. If using Gemini Web fallback, use the same grouping rule.
9. Capture the complete Gemini answer and parse it with `scripts/parse_gemini_license_score.py` or the structured output from `scripts/gemini_license_api.py`. For grouped Gemini API answers, parse the JSON `results` array and then stage/write each license independently. Require one explicit score per license, a complete English introduction per license, source company and license number mentioned when available, and no refusal, identity mismatch, clone risk, revoked/suspended status, unverifiable record, no valid license, no such license, or regulator lookup failure. Do not use Codex-native parsing as a substitute for the script.
9a. If Gemini returns a valid score but flags accuracy uncertainty, do not immediately write. Run targeted secondary verification only for that license, using official broker/regulator/company-register sources. Re-ask Gemini with the specific evidence. Write only when the recheck returns a complete result and `concern_resolution` is resolved/partially resolved with a clear explanation; otherwise mark `needs_review`.
10. Build a staged update record following `data-fields.md` and the confirmed IFXData API contract. For normal score/introduction write-back on an existing license, use `scripts/ifxdata_admin_api.py stage-update` or otherwise submit only the strict `updateLicense` whitelist from `ifxdata-admin-api.md`; do not send the raw `listLicense` record back to `updateLicense`. Modify only `score`, `ai`, `beginTime`, and optional empty enrichment fields that passed validation. Preserve `key`, `licenseId`, identity, address, image, and non-empty contact fields exactly. Stage literal `Invalid Date` beginTime values as `""`. Use `addLicenseToBroker` only when adding licenses or when a user-approved full `licenseList` save is required. Do not write until each staged record points to the same source license and passes validation or has explicit user authorization for a reviewed exception.
11. Save through the confirmed IFXData admin API. Write only:
   - `score`: parsed integer score.
   - `ai`: cleaned English introduction.
   - `country`, `email`, `telphone`, `address`: only when empty in IFXData and concretely provided by Gemini.
   - `beginTime`: only when empty in IFXData and Gemini/source verification returns a concrete `YYYY-MM-DD` date.
12. Verify with a fresh API read of the same Global license record. Mark completion only after API verification succeeds.
13. Continue to the next displayed license. Preserve a resumable result for every license: `completed`, `skipped_existing`, `needs_review`, `blocked`, or `failed_verification`.
14. At batch end, summarize the local result rows. Include the official-website precheck status. Use DeepSeek for the Chinese batch summary when configured; if unavailable, produce the summary locally.

## Browser and API selection

- Use a verified IFXData admin API for license reads/writes when its endpoint and payload have been confirmed from existing project documentation, saved endpoint mapping, or observed authenticated requests.
- Do not guess IFXData write endpoints, HTTP methods, field names, IDs, or language-scope parameters. Confirm the contract before writing.
- Use screenshots only for human troubleshooting or visual confirmation. Do not use screenshots as the primary data extraction method when text/API data is available.
- Browser interaction is always appropriate for Gemini Web and for one-time IFXData endpoint discovery. UI saves are not a normal path and require explicit per-run user authorization after the API failure is reported.
- Browser interaction is also appropriate for opening the broker's official Web link and reading public regulatory disclosures during the precheck.
- Treat API writes and UI saves as state-changing actions. A request to score and fill licenses authorizes updates only for the named broker or explicit batch scope.
- Require read-after-write API verification for normal/batch runs. UI verification is acceptable only during supervised endpoint discovery or a one-off fallback that the user explicitly authorized for that run.

## Automation runtime

- Unattended automation is allowed only in an environment that already has:
  - Gemini API and the confirmed IFXData admin API available without interactive network approval.
  - A valid `QUICKROUTER_API_KEY`, `GEMINI_API_KEY`, or `GOOGLE_AI_STUDIO_API_KEY`, or a signed-in Gemini Web session only for fallback.
  - A valid IFXData admin session/API credential with Global write permission.
- Gemini API calls must be sequential by default: one broker at a time per worker, no parallel license scoring. When using the configured API / relay provider such as Google AI Studio or QuickRouter, target no more than one Gemini request every 20 seconds and pause at least 60 seconds between brokers. Keep a daily safety cap of about 1,000 Gemini scoring calls per API key unless a higher active provider limit is confirmed. Retry HTTP 429 with about 180 seconds then 300 seconds of backoff, then stop with `gemini_rate_limited`. Use `scripts/gemini_license_api.py` because it includes a same-machine shared rate-limit file.
- In heartbeat or scheduled mode, process at most one broker per wake-up. If Gemini returns a valid result, write and verify only the current eligible license/group, then let the next wake-up continue. If an IFXData write times out, first fresh-read the affected record; do not repeat the write unless read-back proves it was not saved.
- DeepSeek network access is optional. If it requires interactive approval, skip DeepSeek translation/reporting and continue local parsing unless the user explicitly requested DeepSeek output.
- For production-scale batches, prefer keeping routine parsing local. If DeepSeek is needed for translation or exception review, route it through an IFXData backend service so Codex calls only IFXData-controlled APIs.
- Browser UI fallback is acceptable only after explicit per-run user authorization. Production automation must use confirmed IFXData APIs for reads, writes, and verification.
- A scheduled run must stop cleanly after its configured batch size or time budget, write a resumable cursor, and avoid infinite retries.

## Local parsing and optional DeepSeek handling

- Parse and validate text exported from Gemini locally:

```bash
python3 scripts/parse_gemini_license_score.py gemini-answer.txt --source license.json
```

- The local parser emits JSON containing `status`, `score`, `introduction`, risk fields, validation metrics, and deterministic validation reasons.
- If parsing returns `needs_review`, do not resolve the narrative with Codex. Ask Gemini once again with the same template or leave the record unresolved.
- Store the assessment text in English. Remove citations only if they are interface artifacts; retain useful source names and URLs when part of Gemini's answer.

DeepSeek support:

- Use DeepSeek for suitable auxiliary work, not final scoring. Preferred commands:

```bash
python3 scripts/deepseek_license_pipeline.py disclosure website-disclosure.txt
python3 scripts/deepseek_license_pipeline.py type-suggest license-or-disclosure.json
python3 scripts/deepseek_license_pipeline.py compress text.txt --max-words 400
python3 scripts/deepseek_license_pipeline.py translate text.txt --target zh
python3 scripts/deepseek_license_pipeline.py exception exception.json
python3 scripts/deepseek_license_pipeline.py report run-results.json
```

- Run redacted preflight for complex exception review:

```bash
python3 scripts/deepseek_license_pipeline.py preflight license.json
```

- The DeepSeek script must block before network calls if redaction fails. Treat `redaction_failed_sensitive_values_remaining` as a hard stop.
- Generate a compact batch report:

```bash
python3 scripts/deepseek_license_pipeline.py report run-results.json
```

Use `DEEPSEEK_MODEL` to override the default cost-focused model. Do not put API keys or redaction mappings in skill files, prompts, logs, or run results.

## Existing values and reruns

- With a non-empty existing Score or AI Score Introduction, default to `skipped_existing` and report it.
- When the user requests refresh/overwrite, capture `previous_score`, `previous_ai_score_introduction`, and the refresh timestamp in the run result before saving.
- A resumed run must skip records already verified `completed` and retry only unresolved records unless the user requests a full refresh.

## Result report

Return the broker name/ID, official website precheck status, Global scope confirmation, total licenses found, and one row per license with institution, license number, score, status, and verification result. List website/backend differences, blocked licenses, or ambiguous licenses separately with the exact reason. Do not claim success for a license that was not freshly verified.
