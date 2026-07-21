# Data fields

## Source license record

| Field | Type | Required | Rule |
|---|---:|---:|---|
| `broker_id` | string | preferred | Stable IFXData broker identifier; never use row position as ID. |
| `broker_name` | string | yes | Exact Global broker name. |
| `license_record_id` | string | preferred | Stable license record identifier when exposed. |
| `display_order` | integer | yes | One-based order shown in the Global License list. |
| `institution_name` | string | yes | Regulator/institution and jurisdiction, e.g. `FCA United Kingdom`. |
| `license_type` | string | yes | Authorization type, e.g. `Market Maker (MM)`. |
| `license_number` | string | yes | Preserve letters, leading zeroes, punctuation, and spacing. |
| `license_begin_date` | string | no | Prefer source `YYYY-MM-DD`; write through the confirmed API field `beginTime` only when the IFXData value is empty and the value is concrete. |
| `license_status` | string | yes | Exact source status, e.g. `Regulated`. |
| `company_registration_name` | string | yes | Exact licensed legal entity. |
| `company_registration_address` | string | no | Normalize repeated whitespace only; never repair/invent address data. |
| `country` | string/null | no | Preserve existing value. If empty, may be enriched from Gemini only when a concrete jurisdiction/country is returned. |
| `email` | string/null | no | Preserve existing value. If empty, may be enriched from Gemini only when a concrete email address is returned. |
| `telephone` | string/null | no | Preserve existing value. IFXData API field may be spelled `telphone`; use confirmed API field spelling. |
| `existing_score` | integer/null | yes | Current Global value before mutation. |
| `existing_ai_score_introduction` | string/null | yes | Current Global value before mutation. |
| `ifxdata_access_mode` | enum | yes | `api` when using confirmed IFXData endpoints; `ui_fallback` when using admin UI. |
| `ifxdata_endpoint_label` | string/null | no | Human-safe label for the confirmed endpoint used; do not store full credentials or cookies. |

## Official website precheck

| Field | Type | Required | Rule |
|---|---:|---:|---|
| `broker_official_website_url` | string/null | yes | Web link from the broker Global page. Prefer API extraction; otherwise read from the Global broker editor UI. |
| `official_website_precheck_status` | enum | yes | `matched`, `differences_found`, `website_unavailable`, `skipped`, or `needs_review`. |
| `checked_pages` | array | yes | Official broker pages inspected, such as homepage, About us, Regulation, Licenses, Legal documents, or footer disclosure pages. |
| `website_disclosed_licenses` | array | no | Website-disclosed regulator/entity/license records used for comparison. |
| `license_comparisons` | array | yes | Per-license comparison objects using statuses from `official-website-precheck.md`. |
| `requires_user_correction_before_scoring` | boolean | yes | `true` when website/backend mismatch should be corrected before Gemini scoring. |

## Gemini assessment

| Field | Type | Required | Rule |
|---|---:|---:|---|
| `provider` | string | yes | Constant `Google Gemini Web`. |
| `queried_at` | string | yes | ISO 8601 timestamp with timezone. |
| `prompt_version` | string | yes | Use `gemini-license-score-v1`. |
| `raw_answer` | string | yes | Full captured answer before cleaning. |
| `score` | integer | yes | Exactly one explicit overall integer, 0–100. |
| `ai_score_introduction` | string | yes | Self-contained English explanation without UI noise. |
| `risk_level` | enum/null | no | `Low`, `Medium`, or `High`; not written unless IFXData adds a field. |
| `investor_significance` | string/null | no | Retain for audit/reporting; not written to another field. |
| `supplemental_country` | string/null | no | Parsed from Gemini `Supplemental fields`; write only into an empty IFXData `country` field. |
| `supplemental_begin_time_of_licence` | string/null | no | Parsed from Gemini `Supplemental fields`; write only if the API field for begin time is confirmed and the IFXData field is empty. |
| `supplemental_email` | string/null | no | Parsed from Gemini `Supplemental fields`; write only into an empty IFXData `email` field. |
| `supplemental_telephone` | string/null | no | Parsed from Gemini `Supplemental fields`; write only into an empty IFXData `telphone`/telephone field. |
| `supplemental_evidence` | string/null | no | One concise explanation for audit; do not write to IFXData unless a dedicated note field exists. |
| `parse_status` | enum | yes | `valid`, `needs_review`, or `blocked`. |

## Optional DeepSeek processing audit

Record these fields only when the optional DeepSeek path is actually used for translation, exception review, or batch reporting. Routine Gemini parsing and validation use the local parser instead.

| Field | Type | Required | Rule |
|---|---:|---:|---|
| `processing_provider` | string | conditional | Constant `DeepSeek API` when used. |
| `processing_model` | string | conditional | Actual API model used when available. |
| `preflight_status` | enum | conditional | `ready`, `needs_review`, or `blocked` when exception review is used. |
| `numbering_regime` | string/null | no | Examples: `FCA FRN`, `SFC CE Number`, `CIRO Dealer Member`. |
| `identity_warnings` | array | conditional | Empty when no warning; never silently discard a mismatch. |
| `format_valid` | boolean | conditional | Post-processing validation result when used. |
| `word_count` | integer | conditional | English introduction word count when DeepSeek touched text. |
| `paragraph_count` | integer | conditional | Blank-line-separated paragraph count when DeepSeek touched text. |
| `api_usage` | object/null | no | Token counts returned by DeepSeek; never include credentials. |

## Update and audit record

```json
{
  "run_id": "20260720T120000+0700-forex-com",
  "broker_id": "<broker id>",
  "broker_name": "FOREX.com",
  "scope": "global",
  "ifxdata_access_mode": "api",
  "ifxdata_endpoint_label": "global_license_update",
  "official_website_precheck": {
    "status": "matched",
    "broker_official_website_url": "https://www.forex.com",
    "checked_pages": [],
    "license_comparisons": [],
    "requires_user_correction_before_scoring": false
  },
  "license_record_id": "<license id>",
  "display_order": 1,
  "identity_key": "fca united kingdom|446717|stonex financial ltd",
  "source": {
    "institution_name": "FCA United Kingdom",
    "license_type": "Market Maker (MM)",
    "license_number": "446717",
    "license_begin_date": "2006-03-24",
    "license_status": "Regulated",
    "company_registration_name": "StoneX Financial Ltd",
    "company_registration_address": "1st Floor Moor House 120 London Wall London EC2Y 5ETE UNITED KINGDOM"
  },
  "assessment": {
    "provider": "Google Gemini Web",
    "prompt_version": "gemini-license-score-v1",
    "queried_at": "2026-07-20T12:00:00+07:00",
    "score": 0,
    "ai_score_introduction": "<Gemini assessment>",
    "risk_level": null,
    "investor_significance": null,
    "supplemental_fields": {
      "country": null,
      "begin_time_of_licence": null,
      "email": null,
      "telephone": null,
      "evidence": null
    }
  },
  "previous": {
    "score": null,
    "ai_score_introduction": null
  },
  "result": {
    "status": "pending",
    "saved_at": null,
    "verified_at": null,
    "verification_mode": "api",
    "error": null
  }
}
```

Normalize `identity_key` by trimming, collapsing whitespace, and lowercasing the three components. Do not remove meaningful license-number punctuation.

Allowed result status values: `pending`, `completed`, `skipped_existing`, `needs_review`, `blocked`, and `failed_verification`.

## Supplemental field write-back

When Gemini returns supplemental values, stage them separately from the score and introduction:

- Only fill IFXData fields that are currently empty, null, or displayed as `-`.
- Never overwrite a non-empty IFXData country, begin date, email, telephone, company, number, type, status, or address from Gemini supplemental output unless the user explicitly asks for correction.
- Validate email with a basic email pattern before writing.
- Validate telephone as a concrete phone-like string with digits before writing.
- Validate begin time as `YYYY-MM-DD` before writing. Use IFXData's confirmed API spelling `beginTime`.
- Use IFXData's confirmed API spelling `telphone` when writing telephone.

## IFXData edit payload fields

For the confirmed `updateLicense` edit API, convert one staged existing license record into:

```json
{
  "key": "<broker_license_row_id>",
  "licenseId": "<license_reference_id>",
  "type": "<license_type>",
  "no": "<license_number>",
  "beginTime": "<license_begin_date or empty>",
  "status": "<license_status>",
  "company": "<company_registration_name>",
  "score": "<score integer or string>",
  "ai": "<ai_score_introduction>",
  "fullName": "<full_name>",
  "country": "<country or empty>",
  "email": "<email or empty>",
  "telphone": "<telephone or empty>",
  "address": "<company_registration_address>",
  "image": "<image url or empty>"
}
```

Use this payload for normal score/introduction updates on existing licenses.

For the confirmed `addLicenseToBroker` add/full-list API, convert one or more staged license records into:

```json
{
  "userId": "<broker_id>",
  "licenseList": [
    {
      "licenseId": "<license_reference_id>",
      "type": "<license_type>",
      "no": "<license_number>",
      "beginTime": "<license_begin_date or empty>",
      "status": "<license_status>",
      "company": "<company_registration_name>",
      "score": "<score integer>",
      "ai": "<ai_score_introduction>",
      "fullName": "<full_name>",
      "country": "<country or empty>",
      "email": "<email or empty>",
      "telphone": "<telephone or empty>",
      "address": "<company_registration_address>",
      "image": "<image url or empty>"
    }
  ]
}
```

Use the latest IFXData source values for preserved fields. Do not synthesize `fullName` from `company` unless the current IFXData source record already lacks `fullName` and the user authorized the fallback.
