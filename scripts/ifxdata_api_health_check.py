#!/usr/bin/env python3
"""Lightweight IFXData API health check for broker license runs.

This script prints no credentials. It verifies whether the current runtime can
reach the confirmed IFXData license-list endpoint with environment-provided
admin headers.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_URL = "http://47.245.121.35:6969/api/v1/admin/broker/listLicense"


def load_local_env() -> str | None:
    """Load IFXDATA_* values from a nearby .env.local if env vars are absent."""

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
            if key.startswith("IFXDATA_") and key not in os.environ:
                os.environ[key] = value
        return str(candidate)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--broker-id", default="220", help="Broker ID to test; default is Doo Prime id 220")
    parser.add_argument("--page-size", default="10")
    parser.add_argument("--page-num", default="1")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()

    local_env_path = load_local_env()
    account = os.getenv("IFXDATA_ADMIN_ACCOUNT") or ""
    password = os.getenv("IFXDATA_ADMIN_PASSWORD") or ""
    result: dict[str, object] = {
        "status": "unknown",
        "credentials": {
            "account_set": bool(account),
            "password_set": bool(password),
            "account_length": len(account) if account else 0,
            "password_length": len(password) if password else 0,
            "source": "environment" if not local_env_path else ".env.local",
        },
        "endpoint_label": "global_license_list",
        "broker_id": args.broker_id,
    }

    if not account or not password:
        result["status"] = "api_unavailable"
        result["reason"] = "missing_environment_credentials"
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    query = urllib.parse.urlencode(
        {"id": args.broker_id, "pageSize": args.page_size, "pageNum": args.page_num}
    )
    req = urllib.request.Request(
        f"{args.url}?{query}",
        headers={
            "x-account": account,
            "x-password": password,
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as response:
            body = response.read().decode("utf-8", "replace")
            result["http_status"] = response.status
    except urllib.error.HTTPError as exc:
        result["status"] = "api_unavailable"
        result["reason"] = "http_error"
        result["http_status"] = exc.code
        result["body_preview"] = exc.read(300).decode("utf-8", "replace")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    except Exception as exc:  # noqa: BLE001 - compact health-check diagnostics
        result["status"] = "api_unavailable"
        result["reason"] = type(exc).__name__
        result["error_preview"] = str(exc)[:300]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        result["status"] = "api_unavailable"
        result["reason"] = "response_not_json"
        result["body_preview"] = body[:300]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    result["status"] = "ok"
    result["response_code"] = payload.get("code")
    result["response_msg"] = payload.get("msg")
    data = payload.get("data")
    result["data_type"] = type(data).__name__
    if isinstance(data, list):
        result["record_count"] = len(data)
        result["first_record_keys"] = sorted(data[0].keys()) if data else []
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
