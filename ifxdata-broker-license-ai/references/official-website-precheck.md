# Official website precheck

Before asking Gemini for license scores, run this precheck once per broker.

## Goal

Use the broker's official website to compare public regulatory disclosures against IFXData Global license records before any Gemini scoring. This catches wrong legal entities, license numbers, missing licenses, extra backend records, or outdated records before AI scoring and write-back.

## Source of website link

Get the broker website from the broker's Global page `Web link` field. Prefer the IFXData admin API if the field is exposed there; otherwise read it from the Global broker editor UI. Record the final URL as `broker_official_website_url`.

If the website link is missing, empty, malformed, or not reachable after one retry, set `official_website_precheck.status = website_unavailable` and continue with existing IFXData Global license records. In that case, if Gemini later reports better identity evidence, report it to the user for manual correction before saving.

## Pages to inspect

Start with the Web link homepage, then inspect likely regulatory disclosure pages such as:

- `About us`
- `Regulation`
- `Licenses`
- `Legal documents`
- footer disclosures
- risk warning / terms pages if they contain entity and license details

Do not use unrelated third-party review sites as the official website source. Official regulator registries can be used as supporting evidence when a mismatch is suspected, but the precheck's first comparison target is the broker's own website disclosure.

## Extract from official website

For each disclosed entity/license, capture:

- regulator or jurisdiction
- license type or authorization scope when shown
- license number or membership/registration number
- legal entity name
- registered address when shown
- disclosure page URL
- exact short note of what was observed, paraphrased if long

Do not invent missing values. Preserve license-number punctuation, letter casing, leading zeroes, and entity suffixes.

## Compare with IFXData Global licenses

For each IFXData Global license, compare against the official website disclosure:

- regulator / institution name
- legal entity name
- license number or membership number
- license status or wording, if disclosed
- address, if disclosed

Use these comparison statuses:

- `matched`: official website and IFXData Global are consistent.
- `website_missing`: IFXData has a license but the official website does not disclose a matching item.
- `backend_missing`: official website discloses a license not present in IFXData Global.
- `number_mismatch`: same regulator/entity but license number differs.
- `entity_mismatch`: regulator or number may match, but legal entity differs.
- `scope_mismatch`: license type or regulated activity differs materially.
- `address_mismatch`: entity and number match, but address differs materially.
- `unclear`: official website wording is too vague for a reliable match.

## Action rules

- If every license is `matched` or only has immaterial wording differences, continue to Gemini scoring.
- If any status is `number_mismatch`, `entity_mismatch`, `scope_mismatch`, or `unclear`, stop before Gemini scoring and report the differences to the user. Let the user correct IFXData first or explicitly authorize continuing with current values.
- If status is `backend_missing` and the missing license evidence is clear, add the missing license directly through the IFXData API without waiting for user confirmation in this workflow. Stop only when required fields are incomplete, entity/number/status is ambiguous, the closest license type is uncertain, or write verification fails.
- If the user explicitly says `你去修改`, `帮我修改`, `可以直接改`, or an equivalent authorization for the current broker, Codex may correct confirmed base fields through the IFXData API before scoring. Only change fields directly supported by official website, regulator registry, company registry, or user-provided corrections. Allowed fields are `type`, `no`, `beginTime`, `status`, `company`, `fullName`, `country`, `email`, `telphone`, and `address`. Never change `key`, `licenseId`, `image`, `score`, or `ai` during this correction stage.
- For `type` corrections, follow [license-type-standardization.md](license-type-standardization.md). Choose the closest existing IFXData `Type of license` value from `broker/getAllLicenseType?language=en` instead of creating free-form wording. If the closest type is uncertain, show the nearest option to the user and ask for confirmation. If no close option exists and the user has authorized license-type maintenance, create a new English license type first, with color `Black`, verify it appears in the list, then use the newly created type. Current mappings: FinCEN/MSB registration -> `Money Services Business`; crypto exchange / virtual asset registration -> `Virtual asset service provider`.
- Before an authorized correction write, show a compact planned-change list. After writing, verify with a fresh API read. If verification fails, stop and report `failed_correction_verification`; do not ask Gemini.
- If the website discloses licenses missing from IFXData, do not ask Gemini to score the backend licenses yet. Give the user the missing-license list first, including concrete fields found from the official website/regulator:
  - `licenseId` / regulator option when known
  - `type`
  - `no`
  - `beginTime`, only if a concrete date is available
  - `status`
  - `company`
  - `fullName`
  - `country`
  - `email`, `telphone`, and `address`, only when clearly tied to the legal/regulatory entity
  - `image`, normally blank unless the existing backend pattern requires a specific uploaded image
  Add clear missing backend records directly through API, then perform a fresh API read before scoring. If the missing record is unclear, stop and report the gap.
- When adding missing licenses, create a staged add draft before writing. Do not infer contact fields from generic support pages unless the page clearly identifies the same regulated entity. If a field is not concretely available, leave it blank. Verify the added row through fresh API read before asking Gemini.
- For regulators that grant multiple regulated activities under one reference number but IFXData does not store combined activity types, split the disclosure into separate IFXData license rows. Example: Hong Kong SFC Type 1, Type 2, and Type 5 under one CE number must be recorded as three rows with the same number/company/address and three different `type` values.
- If IFXData contains a license the website no longer discloses, mark it `website_missing` and run the two-condition expired-license test:
  1. Confirm the broker's official website does not disclose a matching regulator/entity/license-number record after checking the likely regulation/about/legal/footer pages.
  2. Ask Gemini a focused cancellation question using the exact broker name, regulator, country, license type, license number, begin time, status, company, fullName, and address. Require Gemini to answer whether the license has been revoked, cancelled, withdrawn, surrendered, expired, or voluntarily cancelled, and to provide the reason/evidence context.
  If both conditions are satisfied, update IFXData `status` to `Revoked` through `updateLicense`, verify by fresh API read, and leave score/`ai` blank. If either condition is missing, ambiguous, or contradicted, leave the license unchanged and continue the automation.

## Inactive license explanation

For records already marked `Revoked`, `Cancelled`, `Surrendered`, `Withdrawn`, or `Expired`, skip scoring and leave score/`ai` blank by default. Ask Gemini for an inactive-license explanation only when the user explicitly requests it for a specific record.
- If a website cannot be opened, do not block the scoring run. Continue with current IFXData values and record `website_unavailable`.
- If the official website contradicts IFXData but Gemini later provides more reliable regulator-specific evidence, report it to the user and keep the affected license as `needs_review` until corrected.

## User correction checkpoint

When differences are found, summarize them as a compact correction list:

- `backend_missing`: regulator, jurisdiction, legal entity, license number, and page where observed.
- `website_missing`: backend regulator, legal entity, license number, and why no matching website disclosure was found.
- `number_mismatch`, `entity_mismatch`, `scope_mismatch`, `address_mismatch`: show backend value vs website value.

After auto-adding missing licenses, after the user says `已修改`, `已添加`, or otherwise confirms correction, reload IFXData Global licenses through the API and restart the comparison/scoring stage from the fresh backend data. If the user authorizes Codex to modify the fields, write only confirmed field corrections, reload IFXData through the API, and then continue.

## Output record

Store a compact audit object in the run result:

```json
{
  "official_website_precheck": {
    "status": "matched",
    "broker_official_website_url": "https://example.com",
    "checked_pages": ["https://example.com/about-us"],
    "license_comparisons": [
      {
        "display_order": 1,
        "ifxdata_identity_key": "fca united kingdom|446717|example ltd",
        "website_identity_key": "fca united kingdom|446717|example ltd",
        "comparison_status": "matched",
        "notes": "Official website disclosure matches regulator, number, and legal entity."
      }
    ],
    "requires_user_correction_before_scoring": false
  }
}
```
