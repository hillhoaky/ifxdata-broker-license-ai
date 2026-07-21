# DeepSeek pipeline

Use DeepSeek only as an optional supporting layer with redacted placeholders. Gemini Web remains the only provider that decides the license score and substantive assessment. Routine parsing and validation must use the local parser in `scripts/parse_gemini_license_score.py`.

## Configuration

Set `DEEPSEEK_API_KEY` in the execution environment only when optional translation, exception review, or report summarization is requested. The script sends requests to `https://api.deepseek.com/chat/completions` and defaults to `deepseek-v4-flash`. Override the model with `DEEPSEEK_MODEL` and the base URL with `DEEPSEEK_BASE_URL` only for a compatible deployment.

Never print, persist, transmit to Gemini, or place the API key in browser fields. A missing key blocks optional DeepSeek work only; it does not block local Gemini parsing or IFXData write-back.

For unattended automation, DeepSeek must be skipped unless the runtime has non-interactive network access to DeepSeek before the run starts. If a sandbox or desktop approval prompt is required for each API call, skip optional DeepSeek work and continue with local parsing unless the user specifically required DeepSeek output.

For production batches that need DeepSeek translation or exception review, prefer an IFXData backend DeepSeek proxy. Codex then calls IFXData-controlled endpoints and does not directly hold or use the DeepSeek key.

Never send private IFXData values to DeepSeek. Before any DeepSeek call, replace broker names, broker IDs, license record IDs, license numbers, company names, addresses, emails, and phone numbers with placeholders such as `[BROKER_NAME]`, `[LICENSE_NUMBER]`, `[LICENSED_ENTITY]`, and `[REGISTERED_ADDRESS]`. If any original private value remains in the outbound payload, stop with `redaction_failed_sensitive_values_remaining`.

## Commands

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
