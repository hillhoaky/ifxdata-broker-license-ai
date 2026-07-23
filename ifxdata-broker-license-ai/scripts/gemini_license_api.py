#!/usr/bin/env python3
"""Score IFXData broker license records through Google AI Studio Gemini API.

Reads GEMINI_API_KEY or GOOGLE_AI_STUDIO_API_KEY from the environment first,
then a nearby untracked `.env.local`. The key is never printed.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_RATE_LIMIT_DIR = "/tmp/ifxdata-broker-license-ai"


def load_local_env() -> str | None:
    candidates: list[Path] = []
    cwd = Path.cwd()
    script_dir = Path(__file__).resolve().parent
    for base in [cwd, *cwd.parents, script_dir, *script_dir.parents]:
        candidate = base / ".env.local"
        if candidate not in candidates:
            candidates.append(candidate)

    for candidate in candidates:
        if not candidate.is_file():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key in {"GEMINI_API_KEY", "GOOGLE_AI_STUDIO_API_KEY"} and key not in os.environ:
                os.environ[key] = value
        return str(candidate)
    return None


def api_key() -> tuple[str, str | None]:
    source = load_local_env()
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_STUDIO_API_KEY") or ""
    if not key:
        print(json.dumps({"status": "api_unavailable", "reason": "missing_gemini_api_key"}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    return key, source


def normalize_records(data: object) -> list[dict[str, object]]:
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict) and isinstance(data.get("licenses"), list):
        records = data["licenses"]  # type: ignore[assignment]
    elif isinstance(data, dict):
        records = [data]
    else:
        raise ValueError("license input must be a JSON object, array, or object with a licenses array")

    normalized: list[dict[str, object]] = []
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("each license record must be a JSON object")
        normalized.append(item)
    return normalized


def build_prompt(record: dict[str, object]) -> str:
    def value(*names: str) -> str:
        for name in names:
            raw = record.get(name)
            if raw not in (None, ""):
                return str(raw).strip()
        return "Not provided"

    return f"""You are evaluating a forex/CFD broker regulatory license for an investor-facing broker profile.

License information:
- Regulator / Institution: {value("institution", "licenseName", "name", "country")}
- License type: {value("type", "licenseType")}
- License number: {value("no", "licenseNo", "licenseNumber")}
- Begin time of licence: {value("beginTime", "begin_time", "beginDate")}
- Status: {value("status")}
- Registered company name: {value("company", "fullName", "companyName")}
- Registered address: {value("address")}

Task:
Give a comprehensive license quality score out of 100 and a detailed AI Score Introduction.

Important output rules:
1. Output in English only.
2. Use exactly this structure:
Score: <integer from 0 to 100>
AI Score Introduction: <250-450 words>
Risk Level: <Low / Medium / High>
3. Discuss regulator strength, license status, entity/license match, investor protection, operating history, license type implications, and remaining risks.
4. If country, begin date, email, or telephone are concrete and relevant, mention them. If uncertain, do not invent them.
5. Do not include markdown tables, bullets, citations, or source URLs in the final answer.
"""


def build_batch_prompt(records: list[dict[str, object]]) -> str:
    if not 1 <= len(records) <= 3:
        raise ValueError("batch Gemini scoring supports 1 to 3 license records per request")

    def value(record: dict[str, object], *names: str) -> str:
        for name in names:
            raw = record.get(name)
            if raw not in (None, ""):
                return str(raw).strip()
        return "Not provided"

    blocks = []
    for index, record in enumerate(records, start=1):
        blocks.append(
            f"""License {index}
License record ID: {value(record, "key", "licenseRecordId", "id")}
Regulator / Institution: {value(record, "institution", "licenseName", "name", "country")}
License type: {value(record, "type", "licenseType")}
License number: {value(record, "no", "licenseNo", "licenseNumber")}
Begin time of licence: {value(record, "beginTime", "begin_time", "beginDate")}
Status: {value(record, "status")}
Registered company name: {value(record, "company", "fullName", "companyName")}
Registered address: {value(record, "address")}
Missing IFXData fields: {value(record, "missingFields", "missing_fields")}"""
        )

    joined = "\n\n".join(blocks)
    return f"""You are evaluating forex/CFD broker regulatory licenses for investor-facing broker profiles.

Assess each license independently. Do not score the broker's overall trading conditions, spreads, or popularity.

License records:
{joined}

For each license, evaluate regulator credibility, authorization scope, investor protection, compliance strength, license age, current status, legal-entity/license-number match, address match where available, and material uncertainty.

If IFXData is missing country, begin time of licence, email, telephone, or address, provide a supplemental value only when you can identify a concrete value from reliable public information. If a value is not clearly available, use null. Do not guess.

Return valid JSON only. Do not include Markdown, comments, tables, citations, or text outside JSON.

Use exactly this JSON shape:
{{
  "results": [
    {{
      "license_record_id": "<same License record ID from the input>",
      "license_number": "<same license number from the input>",
      "company": "<same registered company name from the input>",
      "score": <integer from 0 to 100>,
      "risk_level": "<Low, Medium, or High>",
      "introduction": "<250-400 English words in four short paragraphs separated by newline newline>",
      "investor_significance": "<one concise English sentence>",
      "supplemental_fields": {{
        "country": "<country/jurisdiction or null>",
        "beginTime": "<YYYY-MM-DD or null>",
        "email": "<email or null>",
        "telphone": "<telephone or null>",
        "address": "<address or null>"
      }},
      "supplemental_evidence": "<one concise sentence or null>"
    }}
  ]
}}
"""


def parse_reply(text: str) -> dict[str, object]:
    score_match = re.search(r"(?im)^\s*Score\s*:\s*(\d{1,3})\b", text)
    risk_match = re.search(r"(?im)^\s*Risk Level\s*:\s*(Low|Medium|High)\b", text)
    intro = text
    intro_match = re.search(r"(?is)AI Score Introduction\s*:\s*(.*?)(?:\n\s*Risk Level\s*:|$)", text)
    if intro_match:
        intro = intro_match.group(1).strip()
    score = int(score_match.group(1)) if score_match else None
    return {
        "score": score,
        "risk_level": risk_match.group(1) if risk_match else None,
        "introduction": intro,
        "word_count": len(intro.split()),
        "raw_reply": text,
        "valid": isinstance(score, int) and 0 <= score <= 100 and bool(intro),
    }


def parse_batch_reply(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"(?is)^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"(?is)\s*```\s*$", "", cleaned).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(?is)\{.*\}", cleaned)
        try:
            payload = json.loads(match.group(0)) if match else {}
        except json.JSONDecodeError:
            payload = {}

    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        return {"results": [], "raw_reply": text, "valid": False, "reason": "missing_results_array"}

    parsed_results: list[dict[str, object]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        intro = str(item.get("introduction") or "").strip()
        score = item.get("score")
        if isinstance(score, str) and score.isdigit():
            score = int(score)
        valid = isinstance(score, int) and 0 <= score <= 100 and bool(intro)
        parsed_results.append(
            {
                "license_record_id": item.get("license_record_id"),
                "license_number": item.get("license_number"),
                "company": item.get("company"),
                "score": score,
                "risk_level": item.get("risk_level"),
                "introduction": intro,
                "investor_significance": item.get("investor_significance"),
                "supplemental_fields": item.get("supplemental_fields") if isinstance(item.get("supplemental_fields"), dict) else {},
                "supplemental_evidence": item.get("supplemental_evidence"),
                "word_count": len(intro.split()),
                "valid": valid,
            }
        )

    return {
        "results": parsed_results,
        "raw_reply": text,
        "valid": bool(parsed_results) and all(bool(item.get("valid")) for item in parsed_results),
    }


def request_gemini(
    prompt: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
    retries: int,
    retry_delay: float,
    retry_backoff: float,
    min_interval: float,
    rate_limit_file: str,
) -> str:
    key, _source = api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    wait_for_shared_rate_limit(min_interval=min_interval, rate_limit_file=rate_limit_file)

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
                break
        except urllib.error.HTTPError as exc:
            body_preview = exc.read(800).decode("utf-8", "replace")
            if exc.code == 429 and attempt < retries:
                time.sleep(retry_delay * (retry_backoff ** attempt))
                continue
            print(json.dumps({"status": "api_unavailable", "reason": "http_error", "http_status": exc.code, "body_preview": body_preview}, ensure_ascii=False, indent=2))
            raise SystemExit(2)
        except Exception as exc:  # noqa: BLE001
            print(json.dumps({"status": "api_unavailable", "reason": type(exc).__name__, "error_preview": str(exc)[:500]}, ensure_ascii=False, indent=2))
            raise SystemExit(2)
    else:
        return ""

    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    return "".join(part.get("text", "") for part in parts if isinstance(part, dict))


def wait_for_shared_rate_limit(*, min_interval: float, rate_limit_file: str) -> None:
    """Coordinate Gemini request spacing across local Codex processes.

    This is intentionally simple and local-machine scoped. It prevents two
    Codex sessions on the same Mac from firing Gemini requests in the same
    short window when they share one AI Studio key/project.
    """
    if min_interval <= 0:
        return

    state_path = Path(rate_limit_file).expanduser()
    state_path.parent.mkdir(parents=True, exist_ok=True)

    with state_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        raw = handle.read().strip()
        try:
            state = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            state = {}

        now = time.time()
        last_request_at = float(state.get("last_request_at") or 0)
        wait_seconds = max(0.0, min_interval - (now - last_request_at))
        if wait_seconds:
            time.sleep(wait_seconds)

        handle.seek(0)
        handle.truncate()
        json.dump({"last_request_at": time.time(), "min_interval": min_interval}, handle)
        handle.flush()
        fcntl.flock(handle, fcntl.LOCK_UN)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--license-json", help="JSON file containing one license record, a JSON array of up to 3 records, or an object with licenses array")
    parser.add_argument("--institution", default="")
    parser.add_argument("--type", default="")
    parser.add_argument("--no", default="")
    parser.add_argument("--begin-time", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--address", default="")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-output-tokens", type=int, default=1600)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--retries", type=int, default=2, help="Retry count for 429 rate-limit responses")
    parser.add_argument("--retry-delay", type=float, default=180, help="Seconds to wait before retrying after 429")
    parser.add_argument("--retry-backoff", type=float, default=1.67, help="Multiplier for each repeated 429 retry delay")
    parser.add_argument(
        "--min-interval",
        type=float,
        default=float(os.getenv("GEMINI_MIN_INTERVAL_SECONDS") or 120),
        help="Minimum seconds between Gemini requests across local Codex processes",
    )
    parser.add_argument(
        "--rate-limit-file",
        default=os.getenv("GEMINI_RATE_LIMIT_FILE") or f"{DEFAULT_RATE_LIMIT_DIR}/gemini-rate-limit.json",
        help="Shared local rate-limit state file",
    )
    args = parser.parse_args()

    if args.license_json:
        input_data = json.loads(Path(args.license_json).read_text(encoding="utf-8"))
    else:
        input_data = {
            "institution": args.institution,
            "type": args.type,
            "no": args.no,
            "beginTime": args.begin_time,
            "status": args.status,
            "company": args.company,
            "address": args.address,
        }
    records = normalize_records(input_data)
    prompt = build_prompt(records[0]) if len(records) == 1 else build_batch_prompt(records)
    max_tokens = args.max_output_tokens if len(records) == 1 else max(args.max_output_tokens, 1600 * len(records))

    reply = request_gemini(
        prompt,
        model=args.model,
        max_tokens=max_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
        retries=args.retries,
        retry_delay=args.retry_delay,
        retry_backoff=args.retry_backoff,
        min_interval=args.min_interval,
        rate_limit_file=args.rate_limit_file,
    )
    parsed = parse_reply(reply) if len(records) == 1 else parse_batch_reply(reply)
    parsed.update({"status": "ok" if parsed["valid"] else "needs_review", "model": args.model})
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return 0 if parsed["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
