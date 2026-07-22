#!/usr/bin/env python3
"""IFXData admin API helper for broker-license scoring runs.

Credentials are read from environment variables first, then a nearby
untracked `.env.local`. This script never prints credential values.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request


LIST_URL = "http://47.245.121.35:6969/api/v1/admin/broker/listLicense"
UPDATE_URL = "http://47.245.121.35:6969/api/v1/admin/broker/updateLicense"
ADD_LIST_URL = "http://47.245.121.35:6969/api/v1/admin/broker/addLicenseToBroker"
UPDATE_LICENSE_FIELDS = [
    "key",
    "licenseId",
    "type",
    "no",
    "beginTime",
    "status",
    "company",
    "score",
    "ai",
    "fullName",
    "country",
    "email",
    "telphone",
    "address",
    "image",
]


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
            if key.startswith("IFXDATA_") and key not in os.environ:
                os.environ[key] = value
        return str(candidate)
    return None


def credentials() -> tuple[str, str, str | None]:
    source = load_local_env()
    account = os.getenv("IFXDATA_ADMIN_ACCOUNT") or ""
    password = os.getenv("IFXDATA_ADMIN_PASSWORD") or ""
    if not account or not password:
        fail(
            "missing_credentials",
            {
                "account_set": bool(account),
                "password_set": bool(password),
                "source": ".env.local" if source else "environment",
            },
        )
    return account, password, source


def fail(reason: str, extra: dict[str, object] | None = None) -> None:
    payload: dict[str, object] = {"status": "api_unavailable", "reason": reason}
    if extra:
        payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(2)


def request_json(
    method: str,
    url: str,
    *,
    query: dict[str, object] | None = None,
    body: dict[str, object] | None = None,
    timeout: float = 20,
) -> dict[str, object]:
    account, password, _source = credentials()
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"
    data = None
    headers = {
        "x-account": account,
        "x-password": password,
        "Accept": "application/json",
    }
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8", "replace")
            http_status = response.status
    except urllib.error.HTTPError as exc:
        fail("http_error", {"http_status": exc.code, "body_preview": exc.read(300).decode("utf-8", "replace")})
    except Exception as exc:  # noqa: BLE001 - compact operational diagnostics
        fail(type(exc).__name__, {"error_preview": str(exc)[:300]})

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        fail("response_not_json", {"http_status": http_status, "body_preview": text[:300]})
    payload["_http_status"] = http_status
    return payload


def read_json_file(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def redact_record(record: dict[str, object]) -> dict[str, object]:
    keys = ["key", "licenseId", "type", "no", "beginTime", "status", "company", "score", "fullName", "country"]
    return {key: record.get(key) for key in keys if key in record}


def clean_begin_time(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if text.lower() == "invalid date":
        return ""
    return text


def build_update_payload(source_record: dict[str, object], *, score: int, ai: str) -> dict[str, object]:
    """Build the strict updateLicense payload accepted by IFXData.

    Do not submit the raw listLicense record; it may contain extra fields that
    cause IFXData validation errors. Keep only the confirmed whitelist.
    """

    payload = {field: source_record.get(field) for field in UPDATE_LICENSE_FIELDS}
    payload["beginTime"] = clean_begin_time(payload.get("beginTime"))
    payload["score"] = int(score)
    payload["ai"] = ai
    return payload


def list_license_records(broker_id: str, *, page_size: str, page_num: str, url: str, timeout: float) -> list[dict[str, object]]:
    payload = request_json(
        "GET",
        url,
        query={"id": broker_id, "pageSize": page_size, "pageNum": page_num},
        timeout=timeout,
    )
    data = payload.get("data")
    if payload.get("code") != 0 or not isinstance(data, list):
        fail("list_license_failed", {"response_code": payload.get("code"), "response_msg": payload.get("msg")})
    return [item for item in data if isinstance(item, dict)]


def find_license(records: list[dict[str, object]], *, key: str | None, license_no: str | None) -> dict[str, object]:
    for record in records:
        if key and str(record.get("key")) == str(key):
            return record
        if license_no and str(record.get("no") or "").strip() == str(license_no).strip():
            return record
    fail("license_not_found", {"key": key, "license_no": license_no})
    raise AssertionError("unreachable")


def cmd_health(args: argparse.Namespace) -> int:
    account, password, source = credentials()
    result = {
        "status": "credentials_ok",
        "credentials": {
            "account_set": bool(account),
            "password_set": bool(password),
            "account_length": len(account),
            "password_length": len(password),
            "source": ".env.local" if source else "environment",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    payload = request_json(
        "GET",
        args.url,
        query={"id": args.broker_id, "pageSize": args.page_size, "pageNum": args.page_num},
        timeout=args.timeout,
    )
    data = payload.get("data")
    result: dict[str, object] = {
        "status": "ok",
        "http_status": payload.get("_http_status"),
        "response_code": payload.get("code"),
        "response_msg": payload.get("msg"),
        "broker_id": args.broker_id,
        "data_type": type(data).__name__,
    }
    if isinstance(data, list):
        result["record_count"] = len(data)
        result["records"] = [redact_record(item) for item in data if isinstance(item, dict)]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    body = read_json_file(args.input)
    if not args.execute:
        print(json.dumps({"status": "dry_run", "operation": "updateLicense", "payload": redact_record(body)}, ensure_ascii=False, indent=2))
        return 0
    payload = request_json("POST", args.url, body=body, timeout=args.timeout)
    print(json.dumps({"status": "submitted", "operation": "updateLicense", "response": payload}, ensure_ascii=False, indent=2))
    return 0


def cmd_stage_update(args: argparse.Namespace) -> int:
    score_result = read_json_file(args.score_result)
    if score_result.get("status") != "ok" or score_result.get("valid") is not True:
        fail("score_result_not_valid", {"score_result": args.score_result})
    score = score_result.get("score")
    introduction = score_result.get("introduction")
    if not isinstance(score, int) or not isinstance(introduction, str) or not introduction.strip():
        fail("score_result_missing_fields", {"score_result": args.score_result})

    records = list_license_records(
        args.broker_id,
        page_size=args.page_size,
        page_num=args.page_num,
        url=args.list_url,
        timeout=args.timeout,
    )
    source = find_license(records, key=args.key, license_no=args.license_no)
    if not args.overwrite and source.get("score") not in (None, ""):
        print(
            json.dumps(
                {
                    "status": "skipped_existing_score",
                    "operation": "stage-update",
                    "source": redact_record(source),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    staged = build_update_payload(source, score=score, ai=introduction)
    if args.output:
        Path(args.output).write_text(json.dumps(staged, ensure_ascii=False, indent=2), encoding="utf-8")

    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "operation": "stage-update",
                    "payload_preview": redact_record(staged),
                    "payload_written": args.output or None,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    response = request_json("POST", args.update_url, body=staged, timeout=args.timeout)
    fresh_records = list_license_records(
        args.broker_id,
        page_size=args.page_size,
        page_num=args.page_num,
        url=args.list_url,
        timeout=args.timeout,
    )
    current = find_license(fresh_records, key=str(staged.get("key")), license_no=None)
    expected_score = str(score)
    actual_score = str(current.get("score")) if current.get("score") is not None else None
    verified_score = actual_score == expected_score
    verified_ai_nonempty = bool(str(current.get("ai") or "").strip())
    print(
        json.dumps(
            {
                "status": "completed" if verified_score and verified_ai_nonempty else "failed_verification",
                "operation": "stage-update",
                "write_response_code": response.get("code"),
                "write_response_msg": response.get("msg"),
                "source": redact_record(source),
                "saved": {
                    "score": score,
                    "current_score": actual_score,
                    "verified_score": verified_score,
                    "verified_ai_nonempty": verified_ai_nonempty,
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if verified_score and verified_ai_nonempty else 2


def cmd_add_list(args: argparse.Namespace) -> int:
    body = read_json_file(args.input)
    license_list = body.get("licenseList")
    preview = license_list if isinstance(license_list, list) else []
    if not args.execute:
        print(
            json.dumps(
                {
                    "status": "dry_run",
                    "operation": "addLicenseToBroker",
                    "userId": body.get("userId"),
                    "license_count": len(preview),
                    "payload_preview": [redact_record(item) for item in preview if isinstance(item, dict)],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    payload = request_json("POST", args.url, body=body, timeout=args.timeout)
    print(json.dumps({"status": "submitted", "operation": "addLicenseToBroker", "response": payload}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    health = sub.add_parser("health")
    health.set_defaults(func=cmd_health)

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--broker-id", required=True)
    list_cmd.add_argument("--page-size", default="10")
    list_cmd.add_argument("--page-num", default="1")
    list_cmd.add_argument("--url", default=LIST_URL)
    list_cmd.add_argument("--timeout", type=float, default=20)
    list_cmd.set_defaults(func=cmd_list)

    update = sub.add_parser("update")
    update.add_argument("--input", required=True, help="JSON file containing the full updateLicense payload")
    update.add_argument("--execute", action="store_true", help="Actually submit the write request")
    update.add_argument("--url", default=UPDATE_URL)
    update.add_argument("--timeout", type=float, default=20)
    update.set_defaults(func=cmd_update)

    stage_update = sub.add_parser("stage-update")
    stage_update.add_argument("--broker-id", required=True)
    group = stage_update.add_mutually_exclusive_group(required=True)
    group.add_argument("--license-no")
    group.add_argument("--key")
    stage_update.add_argument("--score-result", required=True, help="JSON output from gemini_license_api.py")
    stage_update.add_argument("--output", help="Optional path to write the staged whitelist updateLicense payload")
    stage_update.add_argument("--overwrite", action="store_true", help="Allow updating a record with existing score")
    stage_update.add_argument("--execute", action="store_true", help="Actually submit and verify updateLicense")
    stage_update.add_argument("--page-size", default="10")
    stage_update.add_argument("--page-num", default="1")
    stage_update.add_argument("--list-url", default=LIST_URL)
    stage_update.add_argument("--update-url", default=UPDATE_URL)
    stage_update.add_argument("--timeout", type=float, default=20)
    stage_update.set_defaults(func=cmd_stage_update)

    add_list = sub.add_parser("add-list")
    add_list.add_argument("--input", required=True, help="JSON file containing {userId, licenseList}")
    add_list.add_argument("--execute", action="store_true", help="Actually submit the write request")
    add_list.add_argument("--url", default=ADD_LIST_URL)
    add_list.add_argument("--timeout", type=float, default=20)
    add_list.set_defaults(func=cmd_add_list)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
