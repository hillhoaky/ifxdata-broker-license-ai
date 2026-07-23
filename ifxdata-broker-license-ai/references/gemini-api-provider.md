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
3. Target no more than 1 Gemini request per minute per Codex worker when multiple Codex sessions share the same Google AI Studio key/project.
4. Wait at least 60 seconds between license-scoring calls. Pass `--min-interval 60` or set `GEMINI_MIN_INTERVAL_SECONDS=60`; the script uses a shared local rate-limit file so parallel Codex sessions on the same machine queue instead of colliding.
5. After each broker, pause at least 180 seconds before starting the next broker in the same batch.
5a. If a broker has 7 or more eligible licenses, pause 600 seconds after completing, rate-limiting, or otherwise stopping that broker before starting any new broker or unresolved-license retry.
6. Keep a daily safety cap of about 1,000 Gemini scoring calls per API key unless the user confirms a higher active AI Studio limit. This leaves buffer below a typical 1,500 RPD free-tier limit.
7. If Gemini returns HTTP 429, retry with a wide backoff: wait 180 seconds before the first retry and 300 seconds before the second retry.
8. If the request still returns 429 for the same license after the configured retries, stop new Gemini requests for the current broker and report `gemini_rate_limited`.
9. Do not fall back to Gemini Web automatically after rate limiting unless the user explicitly authorizes web fallback.
10. When a grouped response is invalid for only part of a broker, write already-valid parsed results first, then retry only unresolved licenses after a cool-down. If the retry gets 429 or another provider HTTP error, stop and leave those licenses unresolved for a later resume. Do not keep cycling through single-license retries.

Default script controls:

- `GEMINI_MIN_INTERVAL_SECONDS=60`
- `GEMINI_RATE_LIMIT_FILE=/tmp/ifxdata-broker-license-ai/gemini-rate-limit.json`
- `--retries 2`
- `--retry-delay 180`
- use a second retry delay of about 300 seconds; if the script only supports multiplier-based backoff, approximate this with `--retry-backoff 1.67`

When CodexA and CodexB run on different machines or environments, the local shared file cannot coordinate both workers. In that case, keep the same 60-second per-request pace on each worker, pause 180 seconds between brokers, use the 600-second large-broker cool-down, and consider separate AI Studio projects/API keys or an IFXData-owned central queue for production batches.

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

For grouped outputs, bind results to source licenses by the input group order only when `license_record_id` is absent or unreliable and the output count exactly equals the input count. If the result count differs, do not guess; mark the group `needs_review` and retry only after rate limits allow.

## Web fallback

Gemini Web is fallback only when:

- the user explicitly asks to use Gemini Web;
- Gemini API is unavailable for reasons other than routine 429 throttling;
- a one-off human comparison between API output and web output is requested.

When web fallback is used, record `scoring_provider: gemini_web`.
