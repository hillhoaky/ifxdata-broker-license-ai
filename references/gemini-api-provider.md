# Gemini API provider

Use this reference when scoring licenses through Google AI Studio instead of Gemini Web.

## Default provider

- Provider: Google AI Studio Gemini API
- Model: `gemini-2.5-flash`
- Script: `scripts/gemini_license_api.py`
- Required local secret: `GEMINI_API_KEY` or `GOOGLE_AI_STUDIO_API_KEY`
- Generation setting: `thinkingConfig.thinkingBudget = 0`

Keep API keys in environment variables or an untracked local `.env.local`. Never commit API keys, echo them in logs, or place them in run result files.

## Rate-limit policy

Gemini API limits vary by model and billing tier. A run can fail on any of:

- requests per minute (RPM)
- input tokens per minute (TPM)
- requests per day (RPD)
- spend or billing-account caps

For normal broker-license runs, use conservative throughput rather than the theoretical maximum:

1. Process one broker at a time unless the user explicitly authorizes a batch.
2. Process licenses sequentially; do not parallelize Gemini scoring.
3. Target no more than 6 Gemini requests per minute, even if AI Studio shows a higher RPM limit.
4. Wait 8-10 seconds between license-scoring calls.
5. After each broker, pause 30-60 seconds before starting the next broker in the same batch.
6. Keep a daily safety cap of about 1,000 Gemini scoring calls per API key unless the user confirms a higher active AI Studio limit. This leaves buffer below a typical 1,500 RPD free-tier limit.
7. If Gemini returns HTTP 429, wait 60 seconds and retry once.
8. If a second 429 occurs for the same license, stop the broker run and report `gemini_rate_limited`.
9. Do not fall back to Gemini Web automatically after rate limiting unless the user explicitly authorizes web fallback.

For larger batches, use a cursor and resume later instead of forcing retries. Paid Gemini API tiers can provide higher limits; check the active project limits in AI Studio before increasing throughput.

## Output expectations

The API script returns structured JSON:

```json
{
  "status": "ok",
  "model": "gemini-2.5-flash",
  "score": 95,
  "risk_level": "Low",
  "introduction": "...",
  "word_count": 355,
  "valid": true
}
```

Treat `status != "ok"` or `valid != true` as `needs_review` unless the error is clearly a provider outage or rate limit.

## Web fallback

Gemini Web is fallback only when:

- the user explicitly asks to use Gemini Web;
- Gemini API is unavailable for reasons other than routine 429 throttling;
- a one-off human comparison between API output and web output is requested.

When web fallback is used, record `scoring_provider: gemini_web`.
