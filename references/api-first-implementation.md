# API-first implementation

Use this reference to keep IFXData backend operations off the browser UI.

## Principle

After the IFXData admin API contract is confirmed, all IFXData operations must use API calls by default:

- broker lookup
- Global broker detail read, including `Web link`
- Global license list read
- license detail read
- score / AI score introduction update
- read-after-write verification
- result/cursor persistence when supported

Use the confirmed safe mapping in [ifxdata-api-mapping.json](ifxdata-api-mapping.json) as the starting contract. Treat any `unconfirmed` field in that mapping as a blocker for unattended writes until it is resolved.

The browser UI is allowed only for:

- one-time endpoint discovery
- Gemini Web
- official website pages
- supervised troubleshooting when an API call fails or the API contract is unknown

Do not use screenshots as an extraction method for IFXData license fields. Do not dump full DOM snapshots for routine field reads.

## Endpoint discovery once, then cache

When API endpoints are not yet known, perform a one-time supervised discovery pass:

1. Open the target broker in IFXData admin.
2. Use the browser's network/devtools surface to observe authenticated API requests triggered by:
   - broker list search
   - Broker Page / Global detail read
   - License modal open
   - License edit/detail open
   - License score save
   - post-save verification read
3. Record only safe metadata:
   - endpoint label
   - method
   - path pattern without domain-sensitive credentials
   - required query/path/body fields
   - response success signal
   - stable broker ID field
   - stable license record ID field
   - Global language/scope parameter
4. Never record cookies, bearer tokens, session headers, CSRF tokens, or raw full responses containing private data.
5. Store the confirmed mapping in a local run-safe endpoint mapping file, not in the public prompt.

Recommended mapping shape:

```json
{
  "version": 1,
  "confirmed_at": "2026-07-20T00:00:00+07:00",
  "environment": "ifxdata-admin",
  "endpoints": {
    "broker_list": {
      "method": "GET",
      "path_pattern": "<confirmed path>",
      "required_params": ["page", "language"],
      "broker_id_field": "<confirmed field>"
    },
    "broker_global_detail": {
      "method": "GET",
      "path_pattern": "<confirmed path>",
      "web_link_field": "<confirmed field>"
    },
    "global_license_list": {
      "method": "GET",
      "path_pattern": "<confirmed path>",
      "license_record_id_field": "<confirmed field>",
      "global_scope_signal": "<confirmed field/value>"
    },
    "global_license_update": {
      "method": "<PUT/PATCH/POST>",
      "path_pattern": "<confirmed path>",
      "mutable_fields": ["score", "ai_score_introduction"],
      "success_signal": "<confirmed response signal>"
    }
  }
}
```

## Current confirmed update shape

For `global_license_update`, IFXData currently sends the full license record to `broker/updateLicense`. Build the write payload by copying the latest `listLicense` record and modifying only:

- `score`
- `ai`
- missing enrichment fields confirmed in the API payload shape (`country`, `email`, `telphone`) when the source value is empty and Gemini returned a concrete value

Keep fields such as `key`, `licenseId`, `type`, `no`, `status`, `company`, `fullName`, `address`, `country`, `email`, `telphone`, and `image` unchanged unless the user is explicitly correcting license identity data before scoring.

## Runtime API sequence

For a normal broker run:

1. Load the confirmed endpoint mapping.
2. Read broker list/detail via API and resolve the exact broker ID/name.
3. Read the broker Global `Web link` via API.
4. Read Global license list via API.
5. Run official website precheck.
6. For each license, read current detail via API before scoring.
7. Ask Gemini only for eligible licenses.
8. Parse Gemini locally.
9. Stage the update payload from the source record and modify only:
   - `score`
   - `ai`
   - optional empty-field enrichments that passed validation
10. Submit the update via API.
11. Verify by fresh API read.
12. Write one compact result row per license.

## UI fallback limit

UI fallback is not a normal automation path. Use it only when:

- endpoint mapping does not exist yet;
- an API response contradicts the visible UI and needs supervised inspection;
- API write fails and the user explicitly authorizes a one-off UI save.

When UI fallback is used, keep reads targeted:

- no full-page snapshots unless debugging;
- no repeated body text dumps;
- no screenshot-based extraction when text/API fields are available.

Record `ifxdata_access_mode: ui_fallback` and the reason.
