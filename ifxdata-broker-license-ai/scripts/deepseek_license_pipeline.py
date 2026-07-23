#!/usr/bin/env python3
"""DeepSeek-backed processing for the IFXData Gemini license workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Optional


DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-flash"
SENSITIVE_SOURCE_KEYS = {
    "broker_id",
    "broker_name",
    "license_record_id",
    "license_number",
    "company_registration_name",
    "company_registration_address",
    "existing_ai_score_introduction",
    "full_name",
    "email",
    "telephone",
    "address",
}
PLACEHOLDER_BY_KEY = {
    "broker_id": "[BROKER_ID]",
    "broker_name": "[BROKER_NAME]",
    "license_record_id": "[LICENSE_RECORD_ID]",
    "license_number": "[LICENSE_NUMBER]",
    "company_registration_name": "[LICENSED_ENTITY]",
    "company_registration_address": "[REGISTERED_ADDRESS]",
    "existing_ai_score_introduction": "[EXISTING_AI_SCORE_INTRODUCTION]",
    "full_name": "[FULL_NAME]",
    "email": "[EMAIL]",
    "telephone": "[TELEPHONE]",
    "address": "[ADDRESS]",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sensitive_values(source: Optional[dict[str, Any]]) -> list[tuple[str, str]]:
    if not source:
        return []
    values: list[tuple[str, str]] = []
    for key, value in source.items():
        if key not in SENSITIVE_SOURCE_KEYS:
            continue
        if value is None:
            continue
        text = str(value).strip()
        if re.fullmatch(r"\[[A-Z0-9_]+\]", text):
            continue
        if text and text.lower() != "not provided":
            values.append((key, text))
    values.sort(key=lambda item: len(item[1]), reverse=True)
    return values


def redact_text(text: str, source: Optional[dict[str, Any]]) -> tuple[str, dict[str, str]]:
    redacted = text
    mapping: dict[str, str] = {}
    for key, value in sensitive_values(source):
        placeholder = PLACEHOLDER_BY_KEY.get(key, f"[{key.upper()}]")
        if placeholder in mapping and mapping[placeholder] != value:
            placeholder = f"{placeholder[:-1]}_{len(mapping) + 1}]"
        redacted = redacted.replace(value, placeholder)
        mapping[placeholder] = value
    return redacted, mapping


def restore_text(text: Optional[str], mapping: dict[str, str]) -> Optional[str]:
    if not isinstance(text, str):
        return text
    restored = text
    for placeholder, value in mapping.items():
        restored = restored.replace(placeholder, value)
    return restored


def redact_source(source: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    redacted: dict[str, Any] = {}
    mapping: dict[str, str] = {}
    for key, value in source.items():
        if key in SENSITIVE_SOURCE_KEYS and value not in (None, "", "Not provided"):
            placeholder = PLACEHOLDER_BY_KEY.get(key, f"[{key.upper()}]")
            redacted[key] = placeholder
            mapping[placeholder] = str(value)
        else:
            redacted[key] = value
    redacted["redaction_applied"] = True
    return redacted, mapping


def assert_no_sensitive_leak(payload: str, source: Optional[dict[str, Any]]) -> None:
    leaks = []
    for _key, value in sensitive_values(source):
        if value in payload:
            leaks.append(value[:60])
    if leaks:
        raise RuntimeError("redaction_failed_sensitive_values_remaining: " + ", ".join(leaks[:5]))


def call_deepseek(system: str, user: str) -> dict[str, Any]:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured")
    base = os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": 2200,
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"DeepSeek API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DeepSeek API connection failed: {exc.reason}") from exc
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("DeepSeek API returned no choices")
    content = choices[0].get("message", {}).get("content", "")
    if not content.strip():
        raise RuntimeError("DeepSeek API returned empty content")
    result = json.loads(content)
    result["processing_provider"] = "DeepSeek API"
    result["processing_model"] = body.get("model", model)
    result["api_usage"] = body.get("usage")
    return result


def validate_assessment(result: dict[str, Any], raw_answer: str) -> dict[str, Any]:
    score = result.get("score")
    intro = result.get("introduction")
    reasons: list[str] = []
    if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 100:
        reasons.append("score_not_integer_0_100")
    if isinstance(score, int):
        score_re = re.compile(rf"Overall\s+score\s*:\s*{score}\s*(?:/\s*100)?", re.I)
        if not score_re.search(raw_answer):
            reasons.append("score_not_explicit_in_gemini_answer")
    if not isinstance(intro, str) or not intro.strip():
        reasons.append("missing_introduction")
        paragraphs: list[str] = []
        word_count = 0
    else:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", intro.strip()) if part.strip()]
        word_count = len(re.findall(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b", intro))
        if len(paragraphs) != 4:
            reasons.append("introduction_not_four_paragraphs")
        if word_count > 400:
            reasons.append("introduction_word_count_over_400")
        if re.search(r"(?:Overall score|AI score introduction|Risk level|Investor significance)\s*:", intro, re.I):
            reasons.append("introduction_contains_output_labels")
    result["paragraph_count"] = len(paragraphs)
    result["word_count"] = word_count
    result["format_valid"] = not reasons
    if reasons:
        result["status"] = "needs_review"
        result["validation_reasons"] = reasons
    return result


def preflight(source: dict[str, Any]) -> dict[str, Any]:
    redacted_source, mapping = redact_source(source)
    system = """You normalize one redacted financial regulatory license for an automation workflow. Return JSON only. Do not score the license. Do not ask for real company names, license numbers, broker names, addresses, IDs, emails, or phone numbers. Preserve placeholders exactly, identify the regulator's numbering regime from the institution/jurisdiction, select special rules, and provide normalized prompt values using placeholders. CIRO Dealer Members may have no conventional license number; SFC uses a CE Number. Output keys: status (ready|needs_review), normalized_license, numbering_regime, special_rules (array), identity_warnings (array), prompt_values, redaction_preserved (boolean). Mark needs_review only for material ambiguity in the redacted data."""
    user = "Return json for this redacted IFXData Global license record:\n" + json.dumps(redacted_source, ensure_ascii=False)
    assert_no_sensitive_leak(user, source)
    result = call_deepseek(system, user)
    result["redaction_applied"] = True
    result["redaction_mapping_keys"] = sorted(mapping.keys())
    return result


def parse_answer(raw_answer: str, source: Optional[dict[str, Any]]) -> dict[str, Any]:
    redacted_answer, answer_mapping = redact_text(raw_answer, source)
    redacted_source, source_mapping = redact_source(source) if source else (None, {})
    mapping = {**source_mapping, **answer_mapping}
    system = """You parse a redacted Google Gemini regulatory-license assessment. Return JSON only. Never create or change the score: extract the one explicit Overall score from Gemini. Put the complete AI score introduction in the introduction field, including all four blank-line-separated paragraphs between the label 'AI score introduction:' and the label 'Risk level:'. Preserve the substantive English reasoning, uncertainty, and placeholders exactly. Remove UI citation artifacts and output labels from the introduction. Do not put introduction paragraphs in reason. Use reason only for a short error explanation when status is not valid. Do not invent facts. If there is a material identity mismatch, refusal, multiple scores, or unverifiable license warning, use status needs_review. Output keys: status (valid|needs_review|blocked), score (integer|null), introduction (string|null), risk_level (Low|Medium|High|null), investor_significance (string|null), identity_warnings (array), reason (string|null), redaction_preserved (boolean)."""
    payload = {"source": redacted_source, "gemini_answer": redacted_answer}
    user = "Parse and validate this redacted input as json:\n" + json.dumps(payload, ensure_ascii=False)
    assert_no_sensitive_leak(user, source)
    result = call_deepseek(system, user)
    result["introduction"] = restore_text(result.get("introduction"), mapping)
    result["investor_significance"] = restore_text(result.get("investor_significance"), mapping)
    if isinstance(result.get("identity_warnings"), list):
        result["identity_warnings"] = [restore_text(str(item), mapping) for item in result["identity_warnings"]]
    result["redaction_applied"] = True
    result["redaction_mapping_keys"] = sorted(mapping.keys())
    return validate_assessment(result, raw_answer)


def report(results: list[dict[str, Any]]) -> dict[str, Any]:
    compact = [
        {
            "institution": row.get("institution") or row.get("institution_name"),
            "license_number": "[LICENSE_NUMBER]" if row.get("license_number") else None,
            "score": row.get("score"),
            "status": row.get("status"),
            "reason": row.get("reason"),
        }
        for row in results
    ]
    system = """Summarize an IFXData license-processing run. Return concise JSON only with keys total, counts_by_status, completed, unresolved, and summary. Do not add facts beyond the supplied result rows."""
    return call_deepseek(system, "Create the run report as json:\n" + json.dumps(compact, ensure_ascii=False))


def disclosure(text: str) -> dict[str, Any]:
    system = """You structure public regulatory disclosure text for IFXData broker-license prechecks. Return JSON only. Extract only facts explicitly present in the supplied public text. Output keys: status, disclosures, missing_or_unclear, notes. Each disclosure should include regulator, jurisdiction, country, legal_entity, license_number, license_type_or_scope, status, begin_time, address, email, telephone, source_evidence. Use null for absent fields. Do not invent values."""
    return call_deepseek(system, "Structure this public disclosure text as json:\n" + text[:20000])


def type_suggest(data: dict[str, Any]) -> dict[str, Any]:
    redacted, mapping = redact_source(data)
    system = """Suggest the nearest existing IFXData license type for a redacted regulatory license. Return JSON only with keys status, suggested_type, confidence, reason, alternatives, needs_new_type. Do not create a score. Prefer exact official wording and known dropdown values supplied in the input. Preserve placeholders."""
    user = "Suggest license type for this redacted record:\n" + json.dumps(redacted, ensure_ascii=False)
    assert_no_sensitive_leak(user, data)
    result = call_deepseek(system, user)
    result["redaction_applied"] = True
    result["redaction_mapping_keys"] = sorted(mapping.keys())
    return result


def compress_text(text: str, max_words: int) -> dict[str, Any]:
    system = f"""Compress the supplied English IFXData license introduction to at most {max_words} words. Return JSON only with keys status, compressed_text, word_count, changed_meaning. Preserve all substantive risk and regulator reasoning. Do not add facts or scores."""
    return call_deepseek(system, text[:24000])


def translate_text(text: str, target: str) -> dict[str, Any]:
    system = """Translate IFXData operational text. Return JSON only with keys status, translated_text, target_language. Preserve names, license numbers, URLs, and field labels exactly. Do not add facts."""
    return call_deepseek(system, f"Target language: {target}\n\nText:\n{text[:24000]}")


def exception_review(data: dict[str, Any]) -> dict[str, Any]:
    redacted, mapping = redact_source(data)
    system = """Review a redacted IFXData broker-license automation exception. Return JSON only with keys status, issue_type, explanation_zh, next_safe_step, should_retry_now. Do not request private values and do not recommend duplicate writes when read-back verification is needed."""
    user = "Review this redacted exception as json:\n" + json.dumps(redacted, ensure_ascii=False)
    assert_no_sensitive_leak(user, data)
    result = call_deepseek(system, user)
    result["redaction_applied"] = True
    result["redaction_mapping_keys"] = sorted(mapping.keys())
    return result


def redact_command(data: Any) -> Any:
    if isinstance(data, list):
        return [redact_source(item)[0] if isinstance(item, dict) else item for item in data]
    if isinstance(data, dict):
        return redact_source(data)[0]
    raise ValueError("redact input must be a JSON object or array")


def self_test() -> dict[str, Any]:
    raw = "Overall score: 90/100"
    intro = "\n\n".join(["Regulator authority and entity details are clearly described with sufficient supporting context for this deterministic structural test." * 3] * 4)
    checked = validate_assessment({"status": "valid", "score": 90, "introduction": intro}, raw)
    sample_source = {
        "broker_name": "SampleBroker",
        "license_number": "ABC123",
        "company_registration_name": "Sample Capital Ltd",
        "company_registration_address": "1 Private Road",
        "institution_name": "ASIC Australia",
    }
    redacted, mapping = redact_source(sample_source)
    redacted_answer, answer_mapping = redact_text("Overall score: 90/100\nSample Capital Ltd ABC123 1 Private Road", sample_source)
    assert_no_sensitive_leak(json.dumps(redacted, ensure_ascii=False) + redacted_answer, sample_source)
    return {
        "validator_runs": True,
        "paragraph_count": checked["paragraph_count"],
        "format_valid": checked["format_valid"],
        "redaction_runs": True,
        "redacted_placeholders": sorted({*mapping.keys(), *answer_mapping.keys()}),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_pre = sub.add_parser("preflight")
    p_pre.add_argument("source", type=Path)
    p_parse = sub.add_parser("parse")
    p_parse.add_argument("answer", type=Path)
    p_parse.add_argument("--source", type=Path)
    p_report = sub.add_parser("report")
    p_report.add_argument("results", type=Path)
    p_disc = sub.add_parser("disclosure")
    p_disc.add_argument("text", type=Path)
    p_type = sub.add_parser("type-suggest")
    p_type.add_argument("source", type=Path)
    p_comp = sub.add_parser("compress")
    p_comp.add_argument("text", type=Path)
    p_comp.add_argument("--max-words", type=int, default=400)
    p_trans = sub.add_parser("translate")
    p_trans.add_argument("text", type=Path)
    p_trans.add_argument("--target", default="zh")
    p_exc = sub.add_parser("exception")
    p_exc.add_argument("source", type=Path)
    p_redact = sub.add_parser("redact")
    p_redact.add_argument("source", type=Path)
    sub.add_parser("self-test")
    args = parser.parse_args()
    try:
        if args.command == "preflight":
            result = preflight(read_json(args.source))
        elif args.command == "parse":
            source = read_json(args.source) if args.source else None
            result = parse_answer(args.answer.read_text(encoding="utf-8"), source)
        elif args.command == "report":
            data = read_json(args.results)
            if not isinstance(data, list):
                raise ValueError("report input must be a JSON array")
            result = report(data)
        elif args.command == "disclosure":
            result = disclosure(args.text.read_text(encoding="utf-8"))
        elif args.command == "type-suggest":
            result = type_suggest(read_json(args.source))
        elif args.command == "compress":
            result = compress_text(args.text.read_text(encoding="utf-8"), args.max_words)
        elif args.command == "translate":
            result = translate_text(args.text.read_text(encoding="utf-8"), args.target)
        elif args.command == "exception":
            result = exception_review(read_json(args.source))
        elif args.command == "redact":
            result = redact_command(read_json(args.source))
        else:
            result = self_test()
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        result = {"status": "blocked_deepseek_configuration", "reason": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") not in {"needs_review", "blocked", "blocked_deepseek_configuration"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
