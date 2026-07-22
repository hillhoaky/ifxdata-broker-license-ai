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
- If any status is `number_mismatch`, `entity_mismatch`, `scope_mismatch`, `backend_missing`, or `unclear`, stop before Gemini scoring and report the differences to the user. Let the user correct IFXData first or explicitly authorize continuing with current values.
- If the website discloses licenses missing from IFXData, do not ask Gemini to score the backend licenses yet. Give the user the missing-license list first, wait for the user to add/correct the backend records, then perform a fresh API read before scoring.
- If IFXData contains a license the website no longer discloses, report it as `website_missing`. Do not delete or change it unless the user instructs you. If the status is revoked/cancelled and already represented in IFXData, it may be left as-is and skipped unless the user requests scoring.
- If a website cannot be opened, do not block the scoring run. Continue with current IFXData values and record `website_unavailable`.
- If the official website contradicts IFXData but Gemini later provides more reliable regulator-specific evidence, report it to the user and keep the affected license as `needs_review` until corrected.

## User correction checkpoint

When differences are found, summarize them as a compact correction list:

- `backend_missing`: regulator, jurisdiction, legal entity, license number, and page where observed.
- `website_missing`: backend regulator, legal entity, license number, and why no matching website disclosure was found.
- `number_mismatch`, `entity_mismatch`, `scope_mismatch`, `address_mismatch`: show backend value vs website value.

After the user says `已修改`, `已添加`, or otherwise confirms correction, reload IFXData Global licenses through the API and restart the comparison/scoring stage from the fresh backend data.

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
