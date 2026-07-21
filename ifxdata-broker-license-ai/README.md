# IFXData Broker License AI Score

Codex skill package for scoring and updating IFXData broker license records.

This skill supports:

- IFXData broker Global license precheck against the broker's official website.
- Google Gemini Web license scoring.
- Local deterministic parsing and validation.
- API-first IFXData `updateLicense` write-back.
- Optional DeepSeek support only for redacted translation, exception review, or batch reporting.

## Safety model

- Do not commit credentials, cookies, API keys, or raw browser snapshots.
- Use IFXData admin credentials from environment variables:
  - `IFXDATA_ADMIN_ACCOUNT`
  - `IFXDATA_ADMIN_PASSWORD`
- Use DeepSeek credentials from environment variables only when optional redacted processing is explicitly needed.
- Routine scoring and parsing do not require DeepSeek.
- Routine IFXData reads/writes should use API endpoints, not screenshots or manual DevTools extraction.

## Main workflow

1. Read the broker's Global license records from IFXData.
2. Read the broker's Global `Web link`.
3. Compare official website license disclosures against IFXData Global records.
4. Stop for correction if there are material mismatches.
5. Ask Gemini to score each confirmed license.
6. Parse Gemini output locally.
7. Write `score` and `ai` through `updateLicense`.
8. Verify by reading the same license records again.

## Files

- `SKILL.md` — main Codex skill instructions.
- `references/` — workflow references, prompt templates, API mapping, and automation notes.
- `scripts/parse_gemini_license_score.py` — deterministic local Gemini answer parser.
- `scripts/deepseek_license_pipeline.py` — optional redacted DeepSeek helper.
- `agents/openai.yaml` — suggested Codex UI/default prompt metadata.

## Excluded from this repository

Historical test runs are intentionally excluded. They can contain broker-specific audit records and should stay local unless deliberately sanitized.

