---
name: ifxdata-broker-license-ai-score
description: Precheck a broker's official website disclosures against IFXData Global license records, score individual broker licenses with Google Gemini Web, optionally enrich missing country/begin-date/email/telephone fields from concrete Gemini findings, parse and validate Gemini answers locally by deterministic script, and update confirmed fields through IFXData admin APIs. Use for API-first single-broker tests, broker-list batches, resumable processing, verified Global license updates, and optional DeepSeek translation/exception summaries.
---

# IFXData Broker License AI Score

## Hard rules

- Start from `https://admin.ifxdata.com/dashboard/broker-new?page={page}` and process only the broker(s) requested by the user.
- Read and write only the `Global` license record. Do not update other language tabs; they inherit from Global.
- Before license scoring, get the broker's `Web link` from the broker Global page and run an official-website precheck against the Global license records.
- Use IFXData admin APIs for broker lookup, Global broker detail/Web link, Global license enumeration, existing-value checks, saves, and read-after-write verification after the exact authenticated endpoints and payloads are confirmed. For existing license edits, use `POST /api/v1/admin/broker/updateLicense`. Use `POST /api/v1/admin/broker/addLicenseToBroker` only for adding licenses or confirmed full-list saves. Keep credentials in environment variables, never in skill files or logs. Use browser UI only for endpoint discovery, Gemini Web, official website pages, or supervised fallback.
- Do not use screenshots or broad DOM dumps as the primary method for IFXData data extraction. Routine IFXData reads/writes must be API-first to control token usage and reduce UI fragility.
- Treat each license as an independent record. Process licenses in their displayed order unless the user names a specific license.
- Use the signed-in Google Gemini web app at `https://gemini.google.com/app` for the assessment. Do not silently substitute another model.
- Use local deterministic parsing and validation for routine Gemini answers. Do not require DeepSeek for normal scoring, parsing, validation, or write-back.
- When IFXData license fields such as country, begin time of licence, email, or telephone are empty, ask Gemini for optional supplemental values. Fill only concrete values into empty fields; leave unresolved fields blank.
- Use DeepSeek only as optional support for translation, unresolved exception review, or batch report summarization, and only after replacing private IFXData fields with placeholders. Never send broker names, broker IDs, license record IDs, license numbers, company names, addresses, emails, phone numbers, cookies, or raw browser snapshots to DeepSeek.
- Preserve Gemini's substantive English assessment. Remove interface noise and duplicated prompt text, but do not invent, translate, or materially rewrite its reasoning.
- Accept only one explicit integer score from 0 through 100. Never infer a score from tone, category subscores, dates, or license numbers.
- Match a result to the source license using broker ID plus license record ID when available; otherwise require the normalized tuple `(institution, license number, company registration name)`.
- Never overwrite an existing non-empty score without explicit user authorization. Record the old value before an authorized overwrite.
- Do not save partial or ambiguous data. If Gemini is blocked, returns no valid score, or the license identity is uncertain, stop that license and report the issue.
- Never expose credentials, session cookies, tokens, or secrets.

## Required references

- Read [references/gemini-license-score-prompt.md](references/gemini-license-score-prompt.md) before asking Gemini.
- Read [references/local-parser.md](references/local-parser.md) before parsing Gemini answers or staging updates.
- Read [references/official-website-precheck.md](references/official-website-precheck.md) before querying Gemini for any broker.
- Read [references/data-fields.md](references/data-fields.md) before building an update record or payload.
- Read [references/ifxdata-admin-api.md](references/ifxdata-admin-api.md) before reading or writing IFXData license records.
- Load [references/ifxdata-api-mapping.json](references/ifxdata-api-mapping.json) before API-first broker runs and resolve any `unconfirmed` fields before unattended write-back.
- Read [references/api-first-implementation.md](references/api-first-implementation.md) before implementing, batching, or optimizing IFXData access.
- Read [references/automation-workflow.json](references/automation-workflow.json) before batch execution, resuming a run, or implementing orchestration.
- Read [references/automation-runtime.md](references/automation-runtime.md) before creating scheduled, unattended, or batch automation.
- Read [references/deepseek-pipeline.md](references/deepseek-pipeline.md) only before optional DeepSeek translation, reporting, or exception-review stages.

## Workflow

1. Load the confirmed IFXData endpoint mapping. If it is missing, run one supervised endpoint-discovery pass from `api-first-implementation.md` before batch work; do not repeatedly operate from screenshots/DOM for normal runs.
2. Resolve the exact broker through the broker list/detail API. Capture broker name, broker ID, and Global context from API response.
3. From the broker Global detail API, capture the `Web link` official website URL. This is the same Global-page Web link source used by the broker AI score workflow.
4. Read the broker's `Global` license records through the confirmed Global license API.
5. Enumerate all license records in API/display order. Capture the source fields defined in `data-fields.md`, including the stable license record ID.
6. Run the official-website precheck from `official-website-precheck.md`. Compare website-disclosed regulators, legal entities, license numbers, and scopes with IFXData Global license records before scoring:
   - If the official website cannot be opened, continue with current IFXData Global license data and record `website_unavailable`.
   - If the official website shows mismatched company names, license numbers, scopes, or missing/extra licenses, stop before Gemini scoring and report the differences so the user can correct IFXData first.
   - If the user explicitly authorizes continuing despite differences, keep the affected licenses marked for careful review.
7. Run local source checks before querying Gemini. Confirm institution, license type, license number, status, and company registration name are present. Apply known local special rules:
   - Require institution, license type, license number, status, and company registration name.
   - CIRO exception: CIRO supervises firms through Dealer Member status and may not provide an FCA-style standalone license number. For a CIRO Investment Dealer Member, accept `Not applicable — CIRO Dealer Member` as the license-number value and match the record using institution, membership type, exact legal entity, status, and address.
   - Keep an unavailable start date or address as `Not provided`; do not invent it.
   - Flag duplicate license numbers, missing legal entities, or ambiguous identity for review.
8. For each eligible license, use the exact Gemini template. Create a fresh Gemini conversation when practical and submit it to Gemini Web.
9. Capture the complete Gemini answer and parse it with `scripts/parse_gemini_license_score.py`. Require valid JSON, one explicit score, a four-paragraph English introduction of 400 words or fewer, source company and license number mentioned, and no refusal, identity mismatch, clone risk, revoked/suspended status, unverifiable record, no valid license, no such license, or regulator lookup failure. Do not use Codex-native parsing as a substitute for the script.
10. Build a staged update record following `data-fields.md` and the confirmed IFXData API contract. For normal score/introduction write-back on an existing license, submit one full `updateLicense` record copied from the latest source and modify only `score`, `ai`, `beginTime`, and optional empty enrichment fields that passed validation. Preserve `key`, `licenseId`, identity, address, image, and non-empty contact fields exactly. Use `addLicenseToBroker` only when adding licenses or when a user-approved full `licenseList` save is required. Do not write until each staged record points to the same source license and passes validation or has explicit user authorization for a reviewed exception.
11. Save through the confirmed IFXData admin API. Write only:
   - `score`: parsed integer score.
   - `ai`: cleaned English introduction.
   - `country`, `email`, `telphone`: only when empty in IFXData and concretely provided by Gemini.
   - `beginTime`: only when empty in IFXData and Gemini/source verification returns a concrete `YYYY-MM-DD` date.
12. Verify with a fresh API read of the same Global license record. Mark completion only after API verification succeeds.
13. Continue to the next displayed license. Preserve a resumable result for every license: `completed`, `skipped_existing`, `needs_review`, `blocked`, or `failed_verification`.
14. At batch end, summarize the local result rows. Include the official-website precheck status. DeepSeek report summarization is optional and must not block completion.

## Browser and API selection

- Use a verified IFXData admin API for license reads/writes when its endpoint and payload have been confirmed from existing project documentation, saved endpoint mapping, or observed authenticated requests.
- Do not guess IFXData write endpoints, HTTP methods, field names, IDs, or language-scope parameters. Confirm the contract before writing.
- Use screenshots only for human troubleshooting or visual confirmation. Do not use screenshots as the primary data extraction method when text/API data is available.
- Browser interaction is always appropriate for Gemini Web and for one-time IFXData endpoint discovery. UI saves are supervised fallback only, not the normal path.
- Browser interaction is also appropriate for opening the broker's official Web link and reading public regulatory disclosures during the precheck.
- Treat API writes and UI saves as state-changing actions. A request to score and fill licenses authorizes updates only for the named broker or explicit batch scope.
- Require read-after-write API verification for normal/batch runs. UI verification is acceptable only during supervised endpoint discovery or one-off fallback.

## Automation runtime

- Unattended automation is allowed only in an environment that already has:
  - Gemini Web and the confirmed IFXData admin API/browser session available without interactive network approval.
  - A valid signed-in Gemini session or a supported replacement scoring provider explicitly approved by the user.
  - A valid IFXData admin session/API credential with Global write permission.
- DeepSeek network access is optional. If it requires interactive approval, skip DeepSeek translation/reporting and continue local parsing unless the user explicitly requested DeepSeek output.
- For production-scale batches, prefer keeping routine parsing local. If DeepSeek is needed for translation or exception review, route it through an IFXData backend service so Codex calls only IFXData-controlled APIs.
- Browser UI fallback is acceptable for supervised testing, but production automation should use confirmed IFXData APIs for reads, writes, and verification.
- A scheduled run must stop cleanly after its configured batch size or time budget, write a resumable cursor, and avoid infinite retries.

## Local parsing and optional DeepSeek handling

- Parse and validate text exported from Gemini locally:

```bash
python3 scripts/parse_gemini_license_score.py gemini-answer.txt --source license.json
```

- The local parser emits JSON containing `status`, `score`, `introduction`, risk fields, validation metrics, and deterministic validation reasons.
- If parsing returns `needs_review`, do not resolve the narrative with Codex. Ask Gemini once again with the same template or leave the record unresolved.
- Store the assessment text in English. Remove citations only if they are interface artifacts; retain useful source names and URLs when part of Gemini's answer.

DeepSeek is optional:

- Run optional redacted preflight only for complex exception review:

```bash
python3 scripts/deepseek_license_pipeline.py preflight license.json
```

- The DeepSeek script must block before network calls if redaction fails. Treat `redaction_failed_sensitive_values_remaining` as a hard stop.
- Generate an optional compact batch report:

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
