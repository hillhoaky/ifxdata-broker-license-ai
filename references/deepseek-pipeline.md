# DeepSeek pipeline

Use DeepSeek as the default supporting layer for suitable non-scoring tasks when `DEEPSEEK_API_KEY` is configured. Gemini remains the provider for the final license score and substantive score assessment. Local scripts remain responsible for IFXData API reads/writes, deterministic parsing/validation, duplicate checks, and read-after-write verification.

## Allowed DeepSeek tasks

Use DeepSeek for:

- `disclosure_structuring`: turn public official website/regulator disclosure text into structured license rows.
- `difference_summary`: summarize backend-vs-website differences for the user.
- `license_type_suggestion`: suggest the nearest IFXData standard type from public or redacted data.
- `missing_field_candidates`: extract candidate `country`, `beginTime`, `email`, `telphone`, `address`, and `fullName` values from public evidence and current-broker context.
- `text_compression`: shorten Gemini introductions without changing meaning when text is too long.
- `translation`: Chinese/English translation for reports, notes, and type descriptions.
- `summary_report`: Chinese broker/page/batch completion reports.
- `api_log_summary`: summarize compact IFXData/Gemini run logs for the operator.
- `exception_review`: explain API/Gemini/rate-limit/identity mismatch issues.

Do not use DeepSeek for:

- final license scoring;
- revoked/cancelled/withdrawn/surrendered/expired confirmation;
- regulator fact verification that should come from official websites/registers;
- deciding whether an API write is safe;
- deciding whether to add, update, or mark a license inactive;
- IFXData read-after-write verification;
- writing IFXData records;
- parsing score when the local parser succeeds.

## Routing matrix

| Workflow step | DeepSeek usage | Final authority |
|---|---|---|
| Public official website/regulator disclosure structuring | Allowed; send only public text and request candidate license rows | Official source plus IFXData API read |
| Backend-vs-website difference summary | Allowed through `compare`; send only current-broker fields needed for exact comparison, never credentials/cookies/screenshots | Local comparison rules |
| Missing-license candidate draft | Allowed for public disclosure structuring only | IFXData license-type list, local standardization rules, fresh API verification |
| License type suggestion | Allowed when current dropdown options are supplied | `license-type-standardization.md` plus verified dropdown list |
| Missing field candidate extraction | Allowed through `missing-fields`; candidate values only | Gemini supplemental fields plus official evidence; write only into empty IFXData fields |
| Gemini AI Introduction compression | Allowed when text is too long | Gemini substantive answer; DeepSeek must not add facts |
| Chinese page/broker/batch report | Allowed with compact redacted run results | Fresh API verification result |
| API log summary | Allowed through `log-summary` with redaction | Fresh API verification result |
| License type note/range drafting and translation | Allowed; concise English only | User/local type maintenance rules and verified license type list |
| Exception review | Allowed with redacted errors and context | User direction or local safety rules |
| Final score | Not allowed | Gemini |
| License information accuracy / concern resolution | Not allowed | Gemini plus official/regulator evidence |
| Revoked/cancelled confirmation | Not allowed | Official website absence plus focused Gemini cancellation check |
| Regulator fact lookup | Not allowed | Official broker/regulator/company-register sources |
| Write/add/update decision | Not allowed | Local rules, user authorization, IFXData API state |
| Read-after-write verification | Not allowed | IFXData API |

## Configuration

Set `DEEPSEEK_API_KEY` in the execution environment only when optional translation, exception review, or report summarization is requested. The script sends requests to `https://api.deepseek.com/chat/completions` and defaults to `deepseek-v4-flash`. Override the model with `DEEPSEEK_MODEL` and the base URL with `DEEPSEEK_BASE_URL` only for a compatible deployment.

Never print, persist, transmit to Gemini, or place the API key in browser fields. A missing key blocks optional DeepSeek work only; it does not block local Gemini parsing or IFXData write-back.

For unattended automation, DeepSeek must be skipped unless the runtime has non-interactive network access to DeepSeek before the run starts. If a sandbox or desktop approval prompt is required for each API call, skip optional DeepSeek work and continue with local parsing unless the user specifically required DeepSeek output.

For production batches that need DeepSeek translation or exception review, prefer an IFXData backend DeepSeek proxy. Codex then calls IFXData-controlled endpoints and does not directly hold or use the DeepSeek key.

Never send private IFXData values to DeepSeek unless the user explicitly authorizes that exact payload. Before DeepSeek calls involving IFXData backend records, replace broker names, broker IDs, license record IDs, license numbers, company names, addresses, emails, and phone numbers with placeholders such as `[BROKER_NAME]`, `[LICENSE_NUMBER]`, `[LICENSED_ENTITY]`, and `[REGISTERED_ADDRESS]`. If any original private value remains in the outbound payload, stop with `redaction_failed_sensitive_values_remaining`.

Public official website/regulator disclosure text may be sent to DeepSeek for structuring because it is already public and needed for the precheck. Never include credentials, cookies, admin screenshots, or raw private backend snapshots in that public-disclosure payload.

For exact website-vs-backend comparison, send only the current broker's necessary license fields and public official evidence. Never send IFXData admin account/password, cookies, browser screenshots, unrelated brokers, or historical raw runs. If exact private-field comparison is not authorized, run `compare` without `--allow-private`; DeepSeek will produce a limited redacted summary and local rules must do exact matching.

## Commands

### Public disclosure structuring

```bash
python3 scripts/deepseek_license_pipeline.py disclosure website-disclosure.txt
```

Input is public text copied or extracted from a broker's official website or official regulator page. Output JSON contains `disclosures` with regulator/jurisdiction, legal entity, license number, type/scope, country, address, email, telephone, status, and evidence notes when present.

### License type suggestion

```bash
python3 scripts/deepseek_license_pipeline.py type-suggest license-or-disclosure.json
```

Input should include the regulator, country, official wording, current IFXData type if any, and known standard types. Output suggests the closest IFXData type and a short reason. DeepSeek only suggests; local rules and the current dropdown list must still control the final value.

### Website vs backend comparison

```bash
python3 scripts/deepseek_license_pipeline.py compare comparison.json --allow-private
```

Input should contain the current broker's official disclosure rows, current IFXData license rows, and relevant standard license type options. Use `--allow-private` only for the current broker fields needed for exact comparison. Output JSON highlights matched rows, missing backend licenses, extra backend licenses, field mismatches, unclear items, and a concise Chinese summary. DeepSeek does not decide whether to add, update, revoke, or write.

### Missing-field candidates

```bash
python3 scripts/deepseek_license_pipeline.py missing-fields missing-fields.json --allow-private
```

Input should contain public evidence and current IFXData rows. Output candidate values for empty fields only. Generic support contacts should be flagged as `generic_contact_details` rather than written automatically.

### Text compression

```bash
python3 scripts/deepseek_license_pipeline.py compress ai-introduction.txt --max-words 400
```

Use when Gemini produces overly long English text. DeepSeek may shorten wording but must preserve the score rationale and must not add facts.

### Translation

```bash
python3 scripts/deepseek_license_pipeline.py translate text.txt --target zh
```

Use for Chinese reports, type descriptions, or operational summaries.

### Exception review

```bash
python3 scripts/deepseek_license_pipeline.py exception exception.json
```

Use for redacted API/Gemini/rate-limit/identity mismatch issues. Output should explain what happened and the next safe step.

### Optional preflight

```bash
python3 scripts/deepseek_license_pipeline.py preflight license.json
```

Input is one source license record from `data-fields.md`. The script redacts the record before the API call. Use this only for complex exception review or regulator-specific ambiguity that local rules cannot handle.

### Optional parse

```bash
python3 scripts/deepseek_license_pipeline.py parse gemini-answer.txt --source license.json
```

Routine parsing must use `scripts/parse_gemini_license_score.py`. Use DeepSeek parse only when the user explicitly asks for DeepSeek exception review.

### Report

```bash
python3 scripts/deepseek_license_pipeline.py report run-results.json
```

Input is a JSON array of compact per-license results with private identifiers redacted. DeepSeek returns counts and a concise list of unresolved records. Do not send credentials, cookies, raw browser snapshots, raw company names, raw license numbers, raw addresses, or unrelated broker data.

### API log summary

```bash
python3 scripts/deepseek_license_pipeline.py log-summary run-log.json
```

Use for readable Chinese summaries from compact IFXData/Gemini logs. The command recursively redacts common private identifiers before calling DeepSeek. Final success still depends on fresh IFXData API verification.

## Failure policy

- Retry an empty or invalid JSON API response once.
- Do not retry authentication, quota, or permission errors in a loop.
- Route identity mismatches and substantive Gemini warnings to `needs_review`.
- Do not let DeepSeek create a new score. The parsed score must appear explicitly in the Gemini answer.
- Do not fall back to Codex-native parsing or rewriting. Use the local parser for routine parsing, and DeepSeek only for optional support.
- Do not use DeepSeek when redaction cannot be guaranteed.
