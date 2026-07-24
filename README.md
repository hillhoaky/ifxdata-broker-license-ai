# IFXData Broker License AI Score

Codex skill package for scoring and updating IFXData broker license records.

This skill supports:

- IFXData broker Global license precheck against the broker's official website.
- Google Gemini Web license scoring.
- Local deterministic parsing and validation.
- API-first IFXData `updateLicense` write-back.
- Optional DeepSeek support for non-scoring auxiliary work: official disclosure structuring, website-vs-backend difference summaries, license type suggestions, missing-field candidates, Gemini introduction compression, translation, API log summaries, exception review, and batch reporting.

## Safety model

- Do not commit credentials, cookies, API keys, or raw browser snapshots.
- Use IFXData admin credentials from environment variables:
  - `IFXDATA_ADMIN_ACCOUNT`
  - `IFXDATA_ADMIN_PASSWORD`
- Use DeepSeek credentials from environment variables only when optional redacted processing is explicitly needed.
- Routine scoring and parsing do not require DeepSeek. Gemini remains the final scoring source; IFXData API remains the final write/read-back authority.
- DeepSeek must not decide final scores, revoked/cancelled status, write/add/update safety, or read-after-write verification.
- Routine IFXData reads/writes should use API endpoints, not screenshots or manual DevTools extraction.

## Main workflow

1. Read the broker's Global license records from IFXData.
2. Read the broker's Global `Web link`.
3. Compare official website license disclosures against IFXData Global records.
4. Use DeepSeek when configured to structure public disclosure text and summarize current-broker website-vs-backend differences.
5. Stop for correction if there are material mismatches.
6. Ask Gemini to score each confirmed license.
7. Optionally use DeepSeek to compress overlong Gemini introductions or summarize logs.
8. Parse Gemini output locally.
9. Write `score` and `ai` through `updateLicense`.
10. Verify by reading the same license records again.

## Files

- `SKILL.md` — main Codex skill instructions.
- `references/` — workflow references, prompt templates, API mapping, and automation notes.
- `scripts/parse_gemini_license_score.py` — deterministic local Gemini answer parser.
- `scripts/deepseek_license_pipeline.py` — optional redacted DeepSeek helper.
- `agents/openai.yaml` — suggested Codex UI/default prompt metadata.

## Excluded from this repository

Historical test runs are intentionally excluded. They can contain broker-specific audit records and should stay local unless deliberately sanitized.
