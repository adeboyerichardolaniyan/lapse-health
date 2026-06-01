"""@bruin
name: staging.drug_descriptions
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace

depends:
  - marts.drug_opportunities
  - staging.biologic_products

columns:
  - name: opportunity_key
    type: varchar
    description: Opportunity key from marts.drug_opportunities.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: drug_modality
    type: varchar
    description: Opportunity modality represented by the enriched row.
    checks:
      - name: not_null
  - name: label_application_number
    type: varchar
    description: FDA application number used for the successful label match.
  - name: label_match_method
    type: varchar
    description: Match method used against openFDA Drug Labeling.
    checks:
      - name: not_null
  - name: drug_class
    type: varchar
    description: Sanitized established pharmacologic class from openFDA pharm_class_epc.
  - name: mechanism
    type: varchar
    description: Sanitized mechanism class from openFDA pharm_class_moa.
  - name: description
    type: varchar
    description: Sanitized first sentence or clause from openFDA indications_and_usage.
  - name: openfda_set_id
    type: varchar
    description: Label SPL set identifier selected from openFDA when present.
  - name: openfda_effective_time
    type: varchar
    description: Label effective_time selected from openFDA when present.
  - name: openfda_last_updated
    type: varchar
    description: openFDA metadata last_updated value from the response.

custom_checks:
  - name: description keys are unique
    query: select count(*) from (select opportunity_key from staging.drug_descriptions group by 1 having count(*) > 1)
    value: 0
  - name: label match methods are accepted
    query: select count(*) from staging.drug_descriptions where label_match_method not in ('application_number', 'generic_name', 'brand_name', 'unmatched')
    value: 0
  - name: label enrichment text is constrained
    query: select count(*) from staging.drug_descriptions where regexp_matches(coalesce(drug_class, '') || coalesce(mechanism, '') || coalesce(description, ''), '[^A-Za-z0-9,.;:()/%+ -]') or length(coalesce(drug_class, '')) > 160 or length(coalesce(mechanism, '')) > 160 or length(coalesce(description, '')) > 260
    value: 0
  - name: label enrichment rejects placeholder text
    query: select count(*) from staging.drug_descriptions where lower(trim(coalesce(drug_class, ''))) in ('nan', 'null', 'none', 'n/a', 'na') or lower(trim(coalesce(mechanism, ''))) in ('nan', 'null', 'none', 'n/a', 'na') or lower(trim(coalesce(description, ''))) in ('nan', 'null', 'none', 'n/a', 'na')
    value: 0
  - name: label descriptions contain letters
    query: select count(*) from staging.drug_descriptions where description is not null and not regexp_matches(description, '[A-Za-z]')
    value: 0
  - name: label enrichment rejects instruction-like phrases
    query: select count(*) from staging.drug_descriptions where regexp_matches(lower(coalesce(drug_class, '') || ' ' || coalesce(mechanism, '') || ' ' || coalesce(description, '')), 'ignore[[:space:],]+(all[[:space:],]+)?(previous|prior|earlier|system)[[:space:],]+(instructions?|prompts?)') or regexp_matches(lower(coalesce(drug_class, '') || ' ' || coalesce(mechanism, '') || ' ' || coalesce(description, '')), '(reveal|show|print|output|display)[[:space:],]+(the[[:space:],]+)?(system[[:space:],]+prompt|secret[[:space:],]+key|api[[:space:],]+key|password|token)') or regexp_matches(lower(coalesce(drug_class, '') || ' ' || coalesce(mechanism, '') || ' ' || coalesce(description, '')), 'you[[:space:],]+must[[:space:],]+(ignore|reveal|output|print|show|exfiltrate|leak)')
    value: 0
@bruin"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

from bruin import query

OPENFDA_LABEL_API_URL = "https://api.fda.gov/drug/label.json"
OPENFDA_LABEL_DOCS_URL = "https://open.fda.gov/apis/drug/label/"
DEFAULT_LABEL_LIMIT = 50
MAX_LABEL_LIMIT = 100
LABEL_RESULT_LIMIT = 5
MAX_PAGE_BYTES = 5 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 512 * 1024
MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ALLOWED_DOWNLOAD_HOSTS = {"api.fda.gov"}
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]+")
WHITESPACE_PATTERN = re.compile(r"\s+")
SAFE_DISPLAY_PATTERN = re.compile(r"[^A-Za-z0-9,.;:()/%+ \-]+")
CLASS_SUFFIX_PATTERN = re.compile(r"\s*\[(?:EPC|MoA)\]\s*$", re.IGNORECASE)
PLACEHOLDER_TEXT_PATTERN = re.compile(r"[\s./_-]+")
LUCENE_SPECIAL_CHARACTERS = frozenset('+-!(){}[]^"~*?:\\/&|')
SECTION_HEADING_PATTERN = re.compile(
    r"^\s*(?:\d+(?:\.\d+)?\s*)?(INDICATIONS AND USAGE|USES?)\s*",
    re.IGNORECASE,
)
BULLET_PATTERN = re.compile(r"[\u2022\u25e6\u2023\u2043]")
SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")


def materialize() -> list[dict[str, str | None]]:
    candidates = _opportunity_candidates()
    cache: dict[str, tuple[dict[str, Any] | None, str]] = {}
    rows: list[dict[str, str | None]] = []

    for candidate in candidates:
        rows.append(_enrich_candidate(candidate, cache))

    matched = sum(1 for row in rows if row["label_match_method"] != "unmatched")
    described = sum(1 for row in rows if row["description"])
    small_described = sum(
        1 for row in rows if row["drug_modality"] == "small_molecule" and row["description"]
    )
    small_total = sum(1 for row in rows if row["drug_modality"] == "small_molecule")
    small_rate = (small_described / small_total) if small_total else 0
    print(
        "Loaded openFDA label enrichment for "
        f"{len(rows):,} exported opportunities via {OPENFDA_LABEL_DOCS_URL} at "
        f"{datetime.now(UTC).isoformat()}. Matched labels: {matched:,}; "
        f"descriptions: {described:,}; small-molecule description coverage: {small_rate:.0%}."
    )
    return rows


def _opportunity_candidates() -> list[dict[str, Any]]:
    limit = _label_limit()
    frame = query(
        f"""
        select
            opportunities.opportunity_key,
            opportunities.drug_modality,
            opportunities.appl_no,
            opportunities.biologic_product_key,
            opportunities.primary_trade_name,
            opportunities.primary_ingredient,
            biologics.reference_bla_numbers
        from marts.drug_opportunities as opportunities
        left join staging.biologic_products as biologics
            on opportunities.biologic_product_key = biologics.biologic_product_key
        order by opportunities.opportunity_rank
        limit {limit}
        """
    )
    return frame.to_dict("records")


def _label_limit() -> int:
    raw = os.environ.get("LAPSE_LABEL_LIMIT", str(DEFAULT_LABEL_LIMIT))
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_LABEL_LIMIT
    return max(1, min(parsed, MAX_LABEL_LIMIT))


def _enrich_candidate(
    candidate: dict[str, Any],
    cache: dict[str, tuple[dict[str, Any] | None, str]],
) -> dict[str, str | None]:
    application_numbers = _application_numbers(candidate)
    brand_name = _decode_bounded_text(candidate.get("primary_trade_name"))
    generic_name = _decode_bounded_text(candidate.get("primary_ingredient"))

    selected: dict[str, Any] | None = None
    match_method = "unmatched"
    last_updated = ""
    matched_application_number: str | None = None

    for application_number in application_numbers:
        selected, last_updated = _fetch_label(
            f'openfda.application_number:"{application_number}"',
            cache,
        )
        if selected:
            match_method = "application_number"
            matched_application_number = application_number
            break

    if not selected and generic_name:
        selected, last_updated = _fetch_label(
            f'openfda.generic_name:"{_escape_query_term(generic_name)}"',
            cache,
        )
        if selected:
            match_method = "generic_name"

    if not selected and brand_name:
        selected, last_updated = _fetch_label(
            f'openfda.brand_name:"{_escape_query_term(brand_name)}"',
            cache,
        )
        if selected:
            match_method = "brand_name"

    drug_class = _first_class_value(selected, "pharm_class_epc") if selected else None
    mechanism = _first_class_value(selected, "pharm_class_moa") if selected else None
    description = _description(selected) if selected else None

    return {
        "opportunity_key": str(candidate["opportunity_key"]),
        "drug_modality": str(candidate["drug_modality"]),
        "label_application_number": matched_application_number,
        "label_match_method": match_method,
        "drug_class": drug_class,
        "mechanism": mechanism,
        "description": description,
        "openfda_set_id": _selected_set_id(selected),
        "openfda_effective_time": _safe_text(selected.get("effective_time"), 20) if selected else None,
        "openfda_last_updated": _safe_text(last_updated, 20) or None,
    }


def _application_numbers(candidate: dict[str, Any]) -> list[str]:
    values: list[str] = []
    if candidate.get("drug_modality") == "small_molecule":
        appl_no = _digits(candidate.get("appl_no"))
        values.extend(_prefixed_numbers("NDA", appl_no))
    else:
        for bla_number in _split_values(candidate.get("reference_bla_numbers")):
            values.extend(_prefixed_numbers("BLA", _digits(bla_number)))
    return list(dict.fromkeys(value for value in values if value))


def _prefixed_numbers(prefix: str, value: str) -> list[str]:
    if not value:
        return []
    normalized = value.upper()
    if normalized.startswith(prefix):
        normalized = normalized.removeprefix(prefix)
    values = [f"{prefix}{normalized}"]
    stripped = normalized.lstrip("0")
    if stripped and stripped != normalized:
        values.append(f"{prefix}{stripped}")
    return values


def _fetch_label(
    search: str,
    cache: dict[str, tuple[dict[str, Any] | None, str]],
) -> tuple[dict[str, Any] | None, str]:
    if search in cache:
        return cache[search]

    params = {
        "search": search,
        "sort": "effective_time:desc",
        "limit": str(LABEL_RESULT_LIMIT),
    }
    api_key = os.environ.get("OPENFDA_API_KEY")
    if api_key:
        params["api_key"] = api_key

    url = f"{OPENFDA_LABEL_API_URL}?{urllib.parse.urlencode(params)}"
    payload = _fetch_json(url)
    result = _select_label(payload.get("results") or []) if payload else None
    last_updated = _safe_text((payload.get("meta") or {}).get("last_updated"), 20) if payload else ""
    cache[search] = (result, last_updated)
    _respect_rate_limit()
    return cache[search]


def _fetch_json(url: str) -> dict[str, Any] | None:
    _validate_response_host(url)
    opener = urllib.request.build_opener(_AllowlistedRedirectHandler)
    for attempt in range(MAX_RETRIES + 1):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Lapse openFDA label enrichment",
            },
        )
        try:
            with opener.open(request, timeout=60) as response:
                _validate_response_host(response.geturl())
                payload = _read_limited(response)
            return json.loads(payload.decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code not in RETRYABLE_STATUS_CODES or attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "openFDA Drug Labeling request failed with HTTP status "
                    f"{exc.code}; request URL redacted"
                ) from None
            time.sleep(2**attempt)
        except URLError as exc:
            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    f"openFDA Drug Labeling request failed after retries: {exc.reason}"
                ) from None
            time.sleep(2**attempt)
    raise RuntimeError("openFDA label request retry loop exited unexpectedly")


def _select_label(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    usable = [
        result for result in results
        if _description(result)
        or _first_class_value(result, "pharm_class_epc")
        or _first_class_value(result, "pharm_class_moa")
    ]
    if not usable:
        return None
    return max(usable, key=lambda result: _safe_text(result.get("effective_time"), 20))


def _first_class_value(label: dict[str, Any] | None, field: str) -> str | None:
    if not label:
        return None
    values = (label.get("openfda") or {}).get(field) or []
    for value in values:
        cleaned = _optional_safe_text(CLASS_SUFFIX_PATTERN.sub("", _text(value)).strip(), 160)
        if cleaned:
            return cleaned
    return None


def _description(label: dict[str, Any] | None) -> str | None:
    if not label:
        return None
    raw_values = label.get("indications_and_usage") or []
    raw = next((_text(value) for value in raw_values if _text(value)), "")
    if not raw:
        return None

    text = SECTION_HEADING_PATTERN.sub("", CONTROL_CHARACTER_PATTERN.sub(" ", raw)).strip()
    bullet_match = BULLET_PATTERN.search(text)
    if bullet_match:
        text = text[: bullet_match.start()].strip()

    colon_index = text.find(":")
    first_sentence = SENTENCE_BOUNDARY_PATTERN.split(text, maxsplit=1)[0].strip()
    if 35 <= colon_index <= 180 and (not first_sentence or colon_index < len(first_sentence) - 1):
        text = text[:colon_index].strip()
    else:
        text = first_sentence

    text = text.rstrip(":;,. ")
    if not text or not any(char.isalpha() for char in text):
        return None
    if len(text) > 240:
        text = text[:237].rsplit(" ", 1)[0].rstrip(":;,. ") + "..."
    return _optional_safe_text(text, 260)


def _selected_set_id(label: dict[str, Any] | None) -> str | None:
    if not label:
        return None
    openfda = label.get("openfda") or {}
    for field in ("spl_set_id", "spl_id"):
        values = openfda.get(field) or []
        for value in values:
            cleaned = _safe_text(value, 120)
            if cleaned:
                return cleaned
    return _safe_text(label.get("set_id"), 120) or None


def _decode_bounded_text(value: object) -> str:
    text = _text(value)
    match = re.match(r"^DATA START ([A-Za-z0-9+/=]+) DATA END$", text)
    if not match:
        return _safe_text(text, 200)
    try:
        return _safe_text(base64.b64decode(match.group(1)).decode("utf-8"), 200)
    except (ValueError, UnicodeDecodeError):
        return _safe_text(text, 200)


def _escape_query_term(value: str) -> str:
    text = WHITESPACE_PATTERN.sub(" ", CONTROL_CHARACTER_PATTERN.sub(" ", _text(value))).strip()
    return "".join(f"\\{char}" if char in LUCENE_SPECIAL_CHARACTERS else char for char in text)


def _split_values(value: object) -> list[str]:
    return [_text(part) for part in _text(value).split(",") if _text(part)]


def _digits(value: object) -> str:
    return re.sub(r"[^0-9]+", "", _text(value))


def _safe_text(value: object, max_chars: int) -> str:
    without_controls = CONTROL_CHARACTER_PATTERN.sub(" ", _text(value))
    safe = SAFE_DISPLAY_PATTERN.sub(" ", without_controls)
    return WHITESPACE_PATTERN.sub(" ", safe).strip()[:max_chars].strip()


def _optional_safe_text(value: object, max_chars: int) -> str | None:
    cleaned = _safe_text(value, max_chars)
    if not cleaned:
        return None
    normalized = PLACEHOLDER_TEXT_PATTERN.sub("", cleaned).lower()
    return None if normalized in {"nan", "null", "none", "na"} else cleaned


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _respect_rate_limit() -> None:
    delay_seconds = 0.28 if os.environ.get("OPENFDA_API_KEY") else 1.6
    time.sleep(delay_seconds)


def _read_limited(response) -> bytes:
    payload = bytearray()
    while True:
        chunk = response.read(DOWNLOAD_CHUNK_BYTES)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > MAX_PAGE_BYTES:
            raise ValueError(
                "openFDA Drug Labeling response page exceeded the configured limit: "
                f"{len(payload)} bytes > {MAX_PAGE_BYTES} bytes"
            )
    return bytes(payload)


class _AllowlistedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_response_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_response_host(url: str) -> None:
    hostname = urlparse(url).hostname
    if hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError(
            "openFDA Drug Labeling request resolved to an unexpected host: "
            f"{hostname!r}. Allowed hosts: {', '.join(sorted(ALLOWED_DOWNLOAD_HOSTS))}"
        )
