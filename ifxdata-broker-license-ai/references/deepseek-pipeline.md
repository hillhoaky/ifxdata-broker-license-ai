# DeepSeek pipeline

Use DeepSeek as the default supporting layer for suitable non-scoring tasks when `DEEPSEEK_API_KEY` is configured. Gemini remains the provider for the final license score and substantive score assessment. Local scripts remain responsible for IFXData API reads/writes, deterministic parsing/validation, duplicate checks, and read-after-write verification.

## Allowed DeepSeek tasks

Use DeepSeek for:

- `disclosure_structuring`: turn public official website/regulator disclosure text into structured license rows.
- `difference_summary`: summarize backend-vs-website differences for the user.
- `license_type_suggestion`: suggest the nearest IFXData standard type from public or redacted data.
- `text_compression`: shorten Gemini introductions without changing meaning when text is too long.
- `translation`: Chinese/English translation for reports, notes, and type descriptions.
- `summary_report`: Chinese broker/page/batch completion reports.
- `exception_review`: explain API/Gemini/rate-limit/identity mismatch issues.

Do not use DeepSeek for:

- final license scoring;
- regulator fact verification that should come from official websites/registers;
- deciding whether an API write is safe;
- writing IFXData records;
- parsing score when the local parser succeeds.

## Configuration

Set `DEEPSEEK_API_KEY` in the execution environment only when optional translation, exception review, or report summarization is requested. The script sends requests to `https://api.deepseek.com/chat/completions` and defaults to `deepseek-v4-flash`. Override the model with `DEEPSEEK_MODEL` and the base URL with `DEEPSEEK_BASE_URL` only for a compatible deployment.

Never print, persist, transmit to Gemini, or place the API key in browser fields. A missing key blocks optional DeepSeek work only; it does not block local Gemini parsing or IFXData write-back.

For unattended automation, DeepSeek must be skipped unless the runtime has non-interactive network access to DeepSeek before the run starts. If a sandbox or desktop approval prompt is required for each API call, skip optional DeepSeek work and continue with local parsing unless the user specifically required DeepSeek output.

For production batches that need DeepSeek translation or exception review, prefer an IFXData backend DeepSeek proxy. Codex then calls IFXData-controlled endpoints and does not directly hold or use the DeepSeek key.

Never send private IFXData values to DeepSeek unless the user explicitly authorizes that exact payload. Before DeepSeek calls involving IFXData backend records, replace broker names, broker IDs, license record IDs, license numbers, company names, addresses, emails, and phone numbers with placeholders such as `[BROKER_NAME]`, `[LICENSE_NUMBER]`, `[LICENSED_ENTITY]`, and `[REGISTERED_ADDRESS]`. If any original private value remains in the outbound payload, stop with `redaction_failed_sensitive_values_remaining`.

Public official website/regulator disclosure text may be sent to DeepSeek for structuring because it is already public and needed for the precheck. Never include credentials, cookies, admin screenshots, or raw private backend snapshots in that public-disclosure payload.

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

## Failure policy

- Retry an empty or invalid JSON API response once.
- Do not retry authentication, quota, or permission errors in a loop.
- Route identity mismatches and substantive Gemini warnings to `needs_review`.
- Do not let DeepSeek create a new score. The parsed score must appear explicitly in the Gemini answer.
- Do not fall back to Codex-native parsing or rewriting. Use the local parser for routine parsing, and DeepSeek only for optional support.
- Do not use DeepSeek when redaction cannot be guaranteed.
