#!/usr/bin/env python3
"""Local parser for IFXData Gemini license-score answers.

This parser is deliberately deterministic and does not call an external LLM.
Gemini remains the scoring provider; this script only extracts, cleans, and
validates the required fields before IFXData write-back.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RISK_RE = re.compile(r"Risk\s+level\s*:\s*(Low|Medium|High)\b", re.I)
SCORE_RE = re.compile(r"Overall\s+score\s*:\s*(\d{1,3})\s*(?:/\s*100)?", re.I)
INTRO_LABEL_RE = re.compile(r"AI\s+score\s+introduction\s*:\s*", re.I)
INVESTOR_RE = re.compile(r"Investor\s+significance\s*:\s*(.+?)(?:\n\s*Supplemental\s+fields\s*:|\Z)", re.I | re.S)
SUPPLEMENTAL_RE = re.compile(r"Supplemental\s+fields\s*:\s*(.+)", re.I | re.S)
WORD_RE = re.compile(r"\b[A-Za-z]+(?:['’-][A-Za-z]+)*\b")
RISK_TERMS = re.compile(
    r"\b(identity mismatch|mismatch|cannot verify|can't verify|unable to verify|"
    r"unverifiable|revoked|suspended|clone|does not match|no valid license|"
    r"no such license|not found in the regulator)\b",
    re.I,
)
EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s().-]{5,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SOURCE_ARTIFACT_RE = re.compile(
    r"(?m)^\s*(?:"
    r"(?:[A-Z][A-Za-z0-9&.,'’()/-]{1,40}(?:\s+[A-Z][A-Za-z0-9&.,'’()/-]{1,40}){0,4})"
    r"|\+\s*\d+|View\s+all|Sources?|Learn\s+more"
    r")\s*$"
)


def strip_ui_noise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cut_markers = [
        "\n答得好",
        "\n答得不好",
        "\n分享和导出",
        "\n复制",
        "\n显示更多选项",
        "\nGemini 是一款 AI 工具",
    ]
    for marker in cut_markers:
        if marker in text:
            text = text.split(marker, 1)[0]
    text = re.sub(r"\n(?:Sources?|来源|相关内容)\s*:.*", "", text, flags=re.I | re.S)
    text = re.sub(r"\[[0-9]+\]", "", text)
    text = re.sub(r"(?m)^\s*(?:Show more|展开|收起)\s*$", "", text)
    return text.strip()


def extract_between(text: str, start_re: re.Pattern[str], end_re: re.Pattern[str]) -> str | None:
    start = start_re.search(text)
    if not start:
        return None
    rest = text[start.end() :]
    end = end_re.search(rest)
    if not end:
        return rest.strip()
    return rest[: end.start()].strip()


def clean_introduction(intro: str) -> str:
    intro = re.sub(r"(?i)^\s*AI\s+score\s+introduction\s*:\s*", "", intro.strip())
    intro = re.sub(r"(?i)\s*Risk\s+level\s*:\s*(Low|Medium|High).*", "", intro, flags=re.S)
    intro = re.sub(r"(?i)\s*Investor\s+significance\s*:.*", "", intro, flags=re.S)
    intro = re.sub(r"(?m)^\s*(?:Paragraph\s*\d+|Authorization scope|Investor/client-fund protection|Material limitations, uncertainties or risks)\s*:\s*", "", intro)
    intro = SOURCE_ARTIFACT_RE.sub("", intro)
    intro = re.sub(r"[ \t]+", " ", intro)
    intro = re.sub(r"\n[ \t]*\n[ \t]*\n+", "\n\n", intro)
    intro = re.sub(r"\n{3,}", "\n\n", intro)
    return intro.strip()


def normalize_optional_value(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return None
    if re.fullmatch(r"(?i)(not provided|n/a|na|null|none|unknown|not available|unavailable|not found)", value):
        return None
    return value


def parse_supplemental_fields(raw: str) -> tuple[dict[str, str | None], list[str]]:
    supplemental = {
        "country": None,
        "begin_time_of_licence": None,
        "email": None,
        "telephone": None,
        "evidence": None,
    }
    reasons: list[str] = []
    match = SUPPLEMENTAL_RE.search(raw)
    if not match:
        return supplemental, reasons

    block = match.group(1)
    # Stop before common UI or unrelated trailing blocks if browser capture appended them.
    block = re.split(r"\n\s*(?:Sources?|来源|答得好|答得不好|分享和导出)\b", block, flags=re.I)[0]
    labels = {
        "country": r"Country",
        "begin_time_of_licence": r"Begin\s+time\s+of\s+licen[cs]e",
        "email": r"Email",
        "telephone": r"Telephone",
        "evidence": r"Supplemental\s+evidence",
    }
    for key, label in labels.items():
        found = re.search(
            rf"(?im)^\s*{label}\s*:\s*(.+?)(?=\n\s*(?:Country|Begin\s+time\s+of\s+licen[cs]e|Email|Telephone|Supplemental\s+evidence)\s*:|\Z)",
            block,
            flags=re.S,
        )
        if found:
            supplemental[key] = normalize_optional_value(found.group(1).strip().splitlines()[0])

    if supplemental["email"] and not EMAIL_RE.fullmatch(supplemental["email"]):
        reasons.append("supplemental_email_invalid")
        supplemental["email"] = None
    if supplemental["telephone"] and not PHONE_RE.fullmatch(supplemental["telephone"]):
        reasons.append("supplemental_telephone_invalid")
        supplemental["telephone"] = None
    if supplemental["begin_time_of_licence"] and not DATE_RE.fullmatch(supplemental["begin_time_of_licence"]):
        reasons.append("supplemental_begin_time_not_yyyy_mm_dd")
        supplemental["begin_time_of_licence"] = None
    return supplemental, reasons


def paragraph_list(intro: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", intro.strip()) if part.strip()]
    if len(paragraphs) == 1:
        # Some browser captures collapse blank lines. Fall back to line breaks only,
        # but never invent paragraph boundaries inside prose.
        line_parts = [part.strip() for part in intro.splitlines() if part.strip()]
        if len(line_parts) == 4:
            paragraphs = line_parts
    return paragraphs


def parse_answer(raw_answer: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = strip_ui_noise(raw_answer)
    reasons: list[str] = []
    identity_warnings: list[str] = []

    score_matches = SCORE_RE.findall(raw)
    score: int | None
    if len(score_matches) != 1:
        score = None
        reasons.append("score_missing_or_multiple")
    else:
        score = int(score_matches[0])
        if not 0 <= score <= 100:
            reasons.append("score_not_integer_0_100")

    risk_match = RISK_RE.search(raw)
    risk_level = risk_match.group(1).capitalize() if risk_match else None

    intro = extract_between(raw, INTRO_LABEL_RE, RISK_RE)
    if intro is None:
        intro = ""
        reasons.append("missing_introduction")
    intro = clean_introduction(intro)

    paragraphs = paragraph_list(intro)
    word_count = len(WORD_RE.findall(intro))
    if not intro:
        reasons.append("missing_introduction")
    if len(paragraphs) != 4:
        reasons.append("introduction_not_four_paragraphs")
    if word_count > 400:
        reasons.append("introduction_word_count_over_400")
    if re.search(r"(?:Overall score|AI score introduction|Risk level|Investor significance)\s*:", intro, re.I):
        reasons.append("introduction_contains_output_labels")
    if not risk_level:
        reasons.append("missing_risk_level")

    investor = None
    investor_match = INVESTOR_RE.search(raw)
    if investor_match:
        investor = investor_match.group(1).strip().splitlines()[0].strip()

    supplemental_fields, supplemental_reasons = parse_supplemental_fields(raw)

    risk_hits = sorted({m.group(0).lower() for m in RISK_TERMS.finditer(raw)})
    if risk_hits:
        identity_warnings.extend(risk_hits)
        reasons.append("gemini_reported_risk_warning")

    if source:
        company = str(source.get("company_registration_name") or "").strip()
        license_number = str(source.get("license_number") or "").strip()
        if company and company.lower() not in raw.lower():
            reasons.append("source_company_not_mentioned_in_answer")
        if license_number and license_number.lower() not in raw.lower():
            reasons.append("source_license_number_not_mentioned_in_answer")

    status = "valid" if not reasons else "needs_review"
    return {
        "status": status,
        "score": score,
        "introduction": intro,
        "risk_level": risk_level,
        "investor_significance": investor,
        "supplemental_fields": supplemental_fields,
        "supplemental_validation_reasons": supplemental_reasons or None,
        "identity_warnings": identity_warnings,
        "reason": "; ".join(reasons) if reasons else None,
        "processing_provider": "Local deterministic parser",
        "processing_model": None,
        "api_usage": None,
        "paragraph_count": len(paragraphs),
        "word_count": word_count,
        "format_valid": not reasons,
        "validation_reasons": reasons or None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("answer", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8")) if args.source else None
    result = parse_answer(args.answer.read_text(encoding="utf-8"), source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
