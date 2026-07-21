#!/usr/bin/env python3
"""Score one IFXData broker license through Google AI Studio Gemini API.

Reads GEMINI_API_KEY or GOOGLE_AI_STUDIO_API_KEY from the environment first,
then a nearby untracked `.env.local`. The key is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request


DEFAULT_MODEL = "gemini-2.5-flash"


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


def request_gemini(
    prompt: str,
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    timeout: float,
    retries: int,
    retry_delay: float,
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
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8", "replace"))
                break
        except urllib.error.HTTPError as exc:
            body_preview = exc.read(800).decode("utf-8", "replace")
            if exc.code == 429 and attempt < retries:
                time.sleep(retry_delay)
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--license-json", help="JSON file containing one license record")
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
    parser.add_argument("--retries", type=int, default=1, help="Retry count for 429 rate-limit responses")
    parser.add_argument("--retry-delay", type=float, default=60, help="Seconds to wait before retrying after 429")
    args = parser.parse_args()

    if args.license_json:
        record = json.loads(Path(args.license_json).read_text(encoding="utf-8"))
    else:
        record = {
            "institution": args.institution,
            "type": args.type,
            "no": args.no,
            "beginTime": args.begin_time,
            "status": args.status,
            "company": args.company,
            "address": args.address,
        }

    reply = request_gemini(
        build_prompt(record),
        model=args.model,
        max_tokens=args.max_output_tokens,
        temperature=args.temperature,
        timeout=args.timeout,
        retries=args.retries,
        retry_delay=args.retry_delay,
    )
    parsed = parse_reply(reply)
    parsed.update({"status": "ok" if parsed["valid"] else "needs_review", "model": args.model})
    print(json.dumps(parsed, ensure_ascii=False, indent=2))
    return 0 if parsed["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
