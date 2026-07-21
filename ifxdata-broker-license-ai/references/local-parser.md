# Local parser

Use the local parser as the default processing layer after Gemini returns an answer.

```bash
python3 scripts/parse_gemini_license_score.py gemini-answer.txt --source license.json
```

The parser does not call DeepSeek or any external API. It extracts:

- `Overall score`
- `AI score introduction`
- `Risk level`
- `Investor significance`

It validates:

- exactly one integer score from 0 to 100
- one explicit score present in the Gemini answer
- four blank-line-separated English introduction paragraphs
- introduction word count no greater than 400 words
- no output labels inside the introduction
- source company name and license number are mentioned
- Gemini did not report identity mismatch, clone risk, suspended/revoked status, unverifiable records, no valid license, no such license, or regulator lookup failure

It also removes common Gemini/browser citation artifacts when they appear as standalone lines inside the introduction, such as isolated source names, `+ 1`, `Sources`, or `Learn more`. It must not remove regulator or jurisdiction names when they are part of the actual prose.

If validation fails, return `needs_review` and do not write to IFXData. Do not ask Codex to rewrite or repair the assessment unless the user explicitly requests a manual rewrite.

DeepSeek is optional and should be used only for translation, batch-report summarization, or unresolved exception review. DeepSeek is not required for routine parsing, validation, or write-back.
