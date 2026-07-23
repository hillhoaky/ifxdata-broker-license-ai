# IFXData admin API access

Use IFXData admin APIs as the normal access layer for broker-license reads, writes, and verification. Use the admin browser UI only to discover confirmed endpoints, resolve unexpected UI-only data, operate Gemini Web, and inspect official websites. Do not perform browser UI write-back unless the user explicitly authorizes UI fallback for the exact run after the API failure is reported.

API access is required for scalable runs. Screenshots and broad DOM snapshots are too token-expensive and fragile for routine broker/license extraction.

## Endpoint confirmation

Before writing license scores through API, confirm all of these items from existing project notes, saved mappings, or observed authenticated browser requests. This confirmation should be done once and reused:

- Broker lookup/list endpoint and the stable broker ID field.
- Global license list/detail endpoint and the stable license record ID field.
- Save endpoint, HTTP method, required path/query parameters, request body, and response success signal.
- Language/scope parameter that proves the target is `Global`.
- Authentication mechanism already present in the signed-in admin session.

Do not infer or invent an endpoint from route names. If the write contract is incomplete, run endpoint discovery before batch work. Use `ui_fallback` only for a supervised one-off run after explicit user authorization, and record why the API path was unavailable.

Confirmed safe endpoint/path observations from 2026-07-20 are stored in [ifxdata-api-mapping.json](ifxdata-api-mapping.json). Load that mapping before running a broker. If later browser observation contradicts it, stop and refresh the mapping before any write.

## Authentication headers

The license save API uses admin headers:

- `x-account`
- `x-password`

Never hardcode or print the actual values. Load them from local environment variables such as:

- `IFXDATA_ADMIN_ACCOUNT`
- `IFXDATA_ADMIN_PASSWORD`

Run logs and result files may record that credential headers were supplied, but must not record their values.

## Preferred API sequence

0. Run an API health check. Confirm credentials exist without printing them, the broker/license read endpoint is reachable, and the response is parseable/authenticated. If this fails, stop with `api_unavailable`; do not score or write through browser UI unless the user explicitly authorizes UI fallback for this exact run. Prefer the bundled helper:
   - `scripts/ifxdata_admin_api.py health`
   - `scripts/ifxdata_admin_api.py list --broker-id <id>`
1. Read broker list/detail and resolve the exact requested broker.
2. Read the broker's Global license list with stable record IDs.
3. For each license, read the current detail before scoring to capture existing values and identity fields.
4. Stage an edit payload from the latest API source record using the strict `updateLicense` whitelist. Do not submit the raw `listLicense` record because it may contain extra response-only fields that trigger `Validation error`. Preserve all original identity/contact/display fields in the whitelist, and change only the mutable scoring fields required by IFXData:
   - `score`
   - `ai`
   - `beginTime`, only when currently empty and concretely verified as `YYYY-MM-DD`
   - optional enrichment fields that are empty in IFXData and confirmed in the API payload shape, such as `country`, `email`, and `telphone`
5. Submit existing-license edits through `POST /api/v1/admin/broker/updateLicense`. Use `addLicenseToBroker` only for adding licenses or a user-approved full-list save.
6. Perform a fresh API read of the same record and compare saved values exactly.
7. Record request metadata without credentials: endpoint label, method, status code, response ID when present, access mode, saved timestamp, and verified timestamp.

## Confirmed license-type list endpoint

The Global license edit dropdown is sourced from the English license-type table:

```text
GET https://api.ifxdata.com/api/v1/admin/broker/getAllLicenseType?language=en&pageSize=500&pageNum=1
```

Use this endpoint before type corrections. Match by exact `name` first, then by `licenseType`/meaning. Do not write arbitrary type text to a broker license if the value is not present in this list, unless the type has just been created and verified.

Important response fields:

- `id`
- `name`: dropdown/display value used in broker license payload `type`
- `licenseType`
- `typeRange`: range/scope text
- `note`: short introduction
- `color`
- `language`

## Confirmed license-type create endpoint

When no close existing type exists and the user has authorized maintaining license types, create a new English license type before using it on broker licenses:

```text
POST https://api.ifxdata.com/api/v1/admin/broker/addLicenseType
```

Recommended payload shape:

```json
{
  "name": "OTC Derivative Provider",
  "licenseType": "OTC Derivative Provider",
  "typeRange": "Authorises an entity to act as a counterparty or provider for over-the-counter derivative products, subject to the regulator's approved conditions.",
  "note": "An OTC Derivative Provider authorisation allows regulated OTC derivatives business. It is commonly relevant to CFDs and other derivative products.",
  "language": "en",
  "color": "Black"
}
```

Creation rules:

- Fill `name` from the user's intended “enter license name”.
- Fill `typeRange` from “range optional”.
- Fill `note` from “note optional”.
- Use English text only.
- Set `color` to `Black` for newly created types unless the user specifies otherwise.
- After creation, re-read `getAllLicenseType?language=en` and verify the new `name` exists before using it in any broker `updateLicense` payload.

## Confirmed existing-license edit endpoint

Use this endpoint for normal score, AI introduction, and missing-field enrichment on an existing license:

```text
POST http://47.245.121.35:6969/api/v1/admin/broker/updateLicense
```

Bundled helper:

```text
scripts/ifxdata_admin_api.py update --input <payload.json>          # dry run
scripts/ifxdata_admin_api.py update --input <payload.json> --execute # live write
scripts/ifxdata_admin_api.py stage-update --broker-id <id> --license-no <no> --score-result <gemini-result.json>          # build whitelist payload
scripts/ifxdata_admin_api.py stage-update --broker-id <id> --license-no <no> --score-result <gemini-result.json> --execute # build, write, verify
```

Headers:

```text
x-account: <from IFXDATA_ADMIN_ACCOUNT>
x-password: <from IFXDATA_ADMIN_PASSWORD>
Content-Type: application/json
```

Payload shape:

```json
{
  "key": 13476,
  "licenseId": 513,
  "type": "Market Maker (MM)",
  "no": "446717",
  "beginTime": "2006-03-24",
  "status": "Regulated",
  "company": "StoneX Financial Ltd",
  "score": "98",
  "ai": "<cleaned Gemini AI Score Introduction>",
  "fullName": "StoneX Financial Ltd",
  "country": "United Kingdom",
  "email": "sfladvisorycompliance@stonex.com",
  "telphone": "+442035806000",
  "address": "1st Floor Moor House 120 London Wall London EC2Y 5ETE C 2 Y 5 E T UNITED KINGDOM",
  "image": "https://example.com/license-image.jpg"
}
```

The stable broker-license row ID is `key`; the license reference ID is `licenseId`. Build this payload from the latest source record using only the confirmed whitelist below, then setting only the approved mutable fields. `score` may be sent as a string or integer; normalize audit records to an integer.

Confirmed `updateLicense` whitelist:

- `key`
- `licenseId`
- `type`
- `no`
- `beginTime`
- `status`
- `company`
- `score`
- `ai`
- `fullName`
- `country`
- `email`
- `telphone`
- `address`
- `image`

If `beginTime` is the literal API value `Invalid Date`, stage it as an empty string `""`; otherwise IFXData can reject the update with `Validation error`.

Mutable fields for this workflow:

- `score`
- `ai`
- `beginTime`, only when empty and verified
- `country`, only when empty and verified
- `email`, only when empty and verified
- `telphone`, only when empty and verified

Preserved identity/display fields:

- `key`
- `licenseId`
- `type`
- `no`
- `status`
- `company`
- `fullName`
- `address`
- `image`

Do not rename `ai` to `aiScoreIntroduction`. Use `beginTime` for Begin time of licence and `telphone` for Telephone. The success response still needs one live sample; regardless of response body, verify by fresh license read after save.

## Confirmed add/full-list save endpoint

Use:

```text
POST http://47.245.121.35:6969/api/v1/admin/broker/addLicenseToBroker
```

Bundled helper:

```text
scripts/ifxdata_admin_api.py add-list --input <payload.json>          # dry run
scripts/ifxdata_admin_api.py add-list --input <payload.json> --execute # live write
```

Headers:

```text
x-account: <from IFXDATA_ADMIN_ACCOUNT>
x-password: <from IFXDATA_ADMIN_PASSWORD>
Content-Type: application/json
```

Payload shape:

```json
{
  "userId": 150,
  "licenseList": [
    {
      "licenseId": 513,
      "type": "Market Maker (MM)",
      "no": "1",
      "beginTime": "2026-07-21",
      "status": "Offshore Regulated",
      "company": "test Company",
      "score": 11,
      "ai": "test123",
      "fullName": "test Full Name",
      "country": "Country",
      "email": "Email",
      "telphone": "Telephone",
      "address": "Address",
      "image": "https://example.com/license-image.jpg"
    }
  ]
}
```

This endpoint is for adding licenses or confirmed full-list saves. Do not prefer it for existing-license score updates when `updateLicense` is available. Because the endpoint name is `addLicenseToBroker`, treat its list semantics carefully:

- For a single-license supervised test, submit only the user-approved license and verify immediately.
- For unattended/batch updates, prefer sending a complete current `licenseList` for the broker after merging changed fields, unless a live API test proves partial lists are safe and do not remove unchanged licenses.
- Never submit a generated `licenseList` that omits existing licenses unless the user explicitly asked to delete them.

Mutable fields for this workflow:

- `score`
- `ai`
- `beginTime`, only when empty and verified
- `country`, only when empty and verified
- `email`, only when empty and verified
- `telphone`, only when empty and verified

Preserved identity/display fields:

- `licenseId`
- `type`
- `no`
- `status`
- `company`
- `fullName`
- `address`
- `image`

The success response still needs one live sample. Regardless of the response body, verify by fresh license read after save.

For optional missing-field enrichment, only fill empty values already present in the payload shape:

- `country`
- `email`
- `telphone`

For both confirmed write endpoints, the begin-time field is `beginTime`.

## Fallback policy

The default fallback for API failure is to stop, not to write through the UI. Report `api_unavailable` when DNS, network, sandbox, authentication, endpoint, or parse errors prevent API reads/writes.

Use `ui_fallback` only when the user explicitly authorizes it for this exact run and one of these is true:

- The license read/write endpoint is unknown.
- The endpoint is known but the Global scope parameter is uncertain.
- The API response does not expose a stable license record ID.
- The API write fails and no safe retry is available.

For UI fallback, still capture structured text values from page fields wherever possible. Use screenshots only as supporting evidence for a visual anomaly, not as the source of truth. Avoid full DOM/page dumps except when debugging endpoint discovery. Record the exact user authorization phrase, fallback reason, and `ifxdata_access_mode: ui_fallback`.

## Write safety

- Never overwrite an existing non-empty score or introduction unless the user requested refresh/overwrite.
- Never send credentials, cookies, session tokens, or raw browser snapshots to DeepSeek or Gemini.
- Never update non-Global language records.
- Never write a result when the staged identity key differs from the source record's identity key.
- Never mark a license completed until read-after-write verification succeeds.
