# Gemini license score prompt

Use this template with the IFXData Global license fields after the official-website precheck has passed, the user has corrected IFXData, or the user has explicitly authorized continuing. Preserve source spelling unless a previously reviewed correction exists in the run notes. Use `Not provided` only when the IFXData Global record lacks the value.

## Grouping rule

- For 1-3 eligible licenses, one Gemini request is acceptable when the prompt remains readable.
- For 4 or more eligible licenses, split into groups of 2 licenses per Gemini request.
- Do not put more than 2 licenses in one API request unless the user explicitly accepts higher output-quality and rate-limit risk.
- For grouped Gemini API calls, prefer `scripts/gemini_license_api.py` with a JSON file containing either an array of 1-3 license records or `{ "licenses": [...] }`. The script returns a `results` array that must be written back one license at a time.

## Single-license prompt

```text
Based on the information available to you, assess the following financial regulatory license.

Name of institution: {institution_name}
License type: {license_type}
No. of license: {license_number}
Begin time of licence: {license_begin_date}
Status: {license_status}
Company registration name: {company_registration_name}
Company registration address: {company_registration_address}
Current missing fields in IFXData, if any: {missing_fields}

What is the comprehensive score of this license out of 100?

Evaluate the license itself and the match between the regulator, license number, legal entity, status, and address. Consider regulator credibility, authorization scope, investor protection, compliance strength, license age, current status, and any material uncertainty. Do not score the broker's overall trading conditions, spreads, or popularity.

If IFXData is missing country, begin time of licence, email, telephone, or address, also provide supplemental values only when you can identify concrete values from reliable public information. If a value is not clearly available, write `Not provided`. Do not guess.

Return exactly this format in English:

Overall score: <one integer from 0 to 100>/100
AI score introduction:
<Paragraph 1: regulator authority and the match among the license number, legal entity, status, and registered address>

<Paragraph 2: authorization scope and the regulated activities permitted by this license>

<Paragraph 3: investor/client-fund protection, compensation arrangements where applicable, and license age or operating history>

<Paragraph 4: material limitations, uncertainties or risks, followed by the reasons supporting the final score>
Risk level: <Low, Medium, or High>
Investor significance: <one concise sentence>
Supplemental fields:
Country: <country/jurisdiction or Not provided>
Begin time of licence: <YYYY-MM-DD or Not provided>
Email: <email or Not provided>
Telephone: <telephone or Not provided>
Address: <address or Not provided>
Supplemental evidence: <one concise sentence explaining where the supplemental fields came from, or Not provided>
```

## Grouped API prompt behavior

When using `scripts/gemini_license_api.py` with multiple license records, the script asks Gemini to return valid JSON only:

```json
{
  "results": [
    {
      "license_record_id": "14594",
      "license_number": "427848",
      "company": "Example Ltd",
      "score": 88,
      "risk_level": "Low",
      "introduction": "Four short English paragraphs...",
      "investor_significance": "One concise sentence.",
      "supplemental_fields": {
        "country": "Australia",
        "beginTime": "2012-10-12",
        "email": null,
        "telphone": null,
        "address": null
      },
      "supplemental_evidence": "One concise sentence or null."
    }
  ]
}
```

Write each result independently and require the result to match the original license record ID or the tuple `(license number, company)`.

## Query rules

- Start a fresh Gemini conversation for each license when practical to reduce cross-license contamination.
- Do not ask Codex to normalize regulator names, numbering systems, or identity variants through free-form reasoning. Use confirmed IFXData fields, prior reviewed corrections, official-registry evidence, or the optional DeepSeek exception-review path.
- Do not include an expected score or a sample score in the prompt.
- Require substantive license-specific analysis rather than generic praise of the regulator or broker.
- Keep the complete AI score introduction at 400 English words or fewer. Shorter output is acceptable when it is substantive, English, and split into the required four paragraphs.
- Write exactly four short English paragraphs separated by blank lines. Do not add headings, bullets, numbering, or Markdown inside the introduction.
- Do not place source labels, citation fragments, footnote markers, or standalone website names inside the four introduction paragraphs.
- If Gemini says it cannot verify current facts, retain that uncertainty in the introduction; do not convert it into certainty.
- For a CIRO Investment Dealer Member without a standalone license number, use `Not applicable — CIRO Dealer Member` and ask Gemini to verify the exact legal entity's Dealer Member status rather than treating the missing number as a defect.
- If Gemini describes a mismatch, suspended/revoked status, clone risk, or unverifiable license number, retain it and treat the result as `needs_review` before any save.
- If Gemini returns a range or several candidate overall scores, ask it to return one integer using the same required format.
- Supplemental fields are optional enrichment fields, not scoring evidence by themselves. Accept `Not provided` or `null`.
- Only use supplemental field values for IFXData write-back when the corresponding IFXData field is empty and Gemini returns a concrete value. Do not overwrite non-empty source values from this section.
- Do not copy vague phrases such as `available on website`, `publicly listed`, `same as above`, or `not found` into IFXData fields. Treat them as empty.
