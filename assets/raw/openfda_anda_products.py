"""@bruin
name: raw.openfda_anda_products
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace
columns:
  - name: anda_product_key
    type: varchar
    description: Stable key built from ANDA application number and product number.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: application_number
    type: varchar
    description: openFDA Drugs@FDA ANDA application number, including the ANDA prefix.
    checks:
      - name: not_null
  - name: anda_appl_no
    type: varchar
    description: Numeric ANDA application number without the ANDA prefix.
    checks:
      - name: not_null
  - name: product_number
    type: varchar
    description: Product number within the ANDA application.
    checks:
      - name: not_null
  - name: sponsor_name
    type: varchar
    description: Sanitized ANDA sponsor name from Drugs@FDA.
  - name: brand_name
    type: varchar
    description: Sanitized product brand name from Drugs@FDA, commonly the generic product name for ANDAs.
  - name: active_ingredient_names
    type: varchar
    description: Comma-delimited sanitized active ingredient names from the product.
  - name: active_ingredient_strengths
    type: varchar
    description: Comma-delimited sanitized active ingredient strengths from the product.
  - name: dosage_form
    type: varchar
    description: Product dosage form from Drugs@FDA.
  - name: route
    type: varchar
    description: Product route from Drugs@FDA.
  - name: marketing_status
    type: varchar
    description: Product marketing status from Drugs@FDA.
  - name: te_code
    type: varchar
    description: Sanitized therapeutic equivalence code from Drugs@FDA when present.
  - name: reference_drug
    type: varchar
    description: Whether Drugs@FDA marks the product as a reference drug.
  - name: reference_standard
    type: varchar
    description: Whether Drugs@FDA marks the product as a reference standard.
  - name: original_approval_date
    type: varchar
    description: Earliest approved original submission status date in YYYYMMDD text.
  - name: latest_approved_submission_date
    type: varchar
    description: Latest approved submission status date in YYYYMMDD text.
  - name: openfda_last_updated
    type: varchar
    description: openFDA metadata last_updated date for the response.

custom_checks:
  - name: only ANDA applications are loaded
    query: select count(*) from raw.openfda_anda_products where application_number not like 'ANDA%'
    value: 0
  - name: raw ANDA product keys are unique
    query: select count(*) from (select anda_product_key from raw.openfda_anda_products group by 1 having count(*) > 1)
    value: 0
  - name: openFDA text fields are analyst safe
    query: select count(*) from raw.openfda_anda_products where regexp_matches(coalesce(application_number, '') || coalesce(sponsor_name, '') || coalesce(brand_name, '') || coalesce(active_ingredient_names, '') || coalesce(te_code, ''), '[^A-Za-z0-9, ]') or length(coalesce(sponsor_name, '')) > 200 or length(coalesce(brand_name, '')) > 200 or length(coalesce(active_ingredient_names, '')) > 500 or length(coalesce(te_code, '')) > 40
    value: 0
@bruin"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

OPENFDA_DRUGSFDA_API_URL = "https://api.fda.gov/drug/drugsfda.json"
OPENFDA_DRUGSFDA_DOCS_URL = "https://open.fda.gov/apis/drug/drugsfda/"
SEARCH_QUERY = "application_number:ANDA*"
PAGE_LIMIT = 1000
MAX_PAGE_BYTES = 50 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
MAX_RESULTS = 25000
MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ALLOWED_DOWNLOAD_HOSTS = {"api.fda.gov"}
MAX_SHORT_TEXT_CHARS = 200
MAX_INGREDIENT_TEXT_CHARS = 500
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]+")
UNSAFE_ANALYST_TEXT_PATTERN = re.compile(r"[^A-Za-z0-9, ]+")
WHITESPACE_PATTERN = re.compile(r"\s+")


def materialize() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    skip = 0
    total: int | None = None
    last_updated = ""

    while total is None or skip < total:
        page = _fetch_page(skip)
        meta = page.get("meta", {})
        result_meta = meta.get("results", {})
        total = int(result_meta.get("total", 0))
        last_updated = _analyst_safe_text(meta.get("last_updated", ""))

        for application in page.get("results", []):
            rows.extend(_flatten_application(application, last_updated))

        skip += PAGE_LIMIT
        if skip >= MAX_RESULTS and skip < total:
            raise ValueError(
                "openFDA ANDA query returned more rows than the supported pagination limit: "
                f"{total:,} results > {MAX_RESULTS:,}. Refine pagination before ingesting."
            )

    print(
        f"Loaded {len(rows):,} ANDA product rows from openFDA Drugs@FDA "
        f"({total:,} applications, last_updated={last_updated}) via "
        f"{OPENFDA_DRUGSFDA_DOCS_URL} at {datetime.now(UTC).isoformat()}"
    )
    return rows


def _fetch_page(skip: int) -> dict:
    params = {
        "search": SEARCH_QUERY,
        "sort": "application_number:asc",
        "limit": str(PAGE_LIMIT),
        "skip": str(skip),
    }
    url = f"{OPENFDA_DRUGSFDA_API_URL}?{urllib.parse.urlencode(params)}"
    _validate_response_host(url)
    opener = urllib.request.build_opener(_AllowlistedRedirectHandler)

    for attempt in range(MAX_RETRIES + 1):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "Lapse openFDA ANDA ingestion",
            },
        )
        try:
            with opener.open(request, timeout=120) as response:
                _validate_response_host(response.geturl())
                payload = _read_limited(response)
            return json.loads(payload.decode("utf-8"))
        except HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS_CODES or attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "openFDA Drugs@FDA request failed with HTTP status "
                    f"{exc.code} for skip={skip}; request URL redacted"
                ) from None
            time.sleep(2**attempt)
        except URLError as exc:
            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "openFDA Drugs@FDA request failed after retries for "
                    f"skip={skip}: {exc.reason}"
                ) from None
            time.sleep(2**attempt)

    raise RuntimeError("openFDA request retry loop exited unexpectedly")


def _flatten_application(application: dict, last_updated: str) -> list[dict[str, str]]:
    application_number = _analyst_safe_text(application.get("application_number")).upper()
    anda_appl_no = application_number.removeprefix("ANDA")
    sponsor_name = _analyst_safe_text(application.get("sponsor_name"))
    submissions = application.get("submissions") or []
    original_approval_date = _original_approval_date(submissions)
    latest_approved_submission_date = _latest_approved_submission_date(submissions)

    rows = []
    for product in application.get("products") or []:
        product_number = _text(product.get("product_number"))
        ingredient_names = _join_values(
            ingredient.get("name")
            for ingredient in product.get("active_ingredients") or []
        )
        ingredient_strengths = _join_values(
            ingredient.get("strength")
            for ingredient in product.get("active_ingredients") or []
        )

        rows.append(
            {
                "anda_product_key": f"{application_number}-{product_number}",
                "application_number": application_number,
                "anda_appl_no": anda_appl_no,
                "product_number": product_number,
                "sponsor_name": sponsor_name,
                "brand_name": _analyst_safe_text(product.get("brand_name")),
                "active_ingredient_names": ingredient_names,
                "active_ingredient_strengths": ingredient_strengths,
                "dosage_form": _analyst_safe_text(product.get("dosage_form")),
                "route": _analyst_safe_text(product.get("route")),
                "marketing_status": _analyst_safe_text(product.get("marketing_status")),
                "te_code": _analyst_safe_text(product.get("te_code")).upper(),
                "reference_drug": _yes_no(product.get("reference_drug")),
                "reference_standard": _yes_no(product.get("reference_standard")),
                "original_approval_date": original_approval_date,
                "latest_approved_submission_date": latest_approved_submission_date,
                "openfda_last_updated": last_updated,
            }
        )

    return rows


def _original_approval_date(submissions: Iterable[dict]) -> str:
    dates = [
        _text(submission.get("submission_status_date"))
        for submission in submissions
        if _text(submission.get("submission_type")).upper() == "ORIG"
        and _text(submission.get("submission_status")).upper() == "AP"
        and _text(submission.get("submission_status_date"))
    ]
    return min(dates, default="")


def _latest_approved_submission_date(submissions: Iterable[dict]) -> str:
    dates = [
        _text(submission.get("submission_status_date"))
        for submission in submissions
        if _text(submission.get("submission_status")).upper() == "AP"
        and _text(submission.get("submission_status_date"))
    ]
    return max(dates, default="")


def _join_values(values: Iterable[object]) -> str:
    cleaned = sorted({_analyst_safe_text(value) for value in values if _text(value)})
    return _limit_text(", ".join(cleaned), MAX_INGREDIENT_TEXT_CHARS)


def _yes_no(value: object) -> str:
    normalized = _text(value).lower()
    if normalized == "yes":
        return "Yes"
    if normalized == "no":
        return "No"
    return _text(value)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _analyst_safe_text(value: object) -> str:
    without_controls = CONTROL_CHARACTER_PATTERN.sub(" ", _text(value))
    safe = UNSAFE_ANALYST_TEXT_PATTERN.sub(" ", without_controls)
    return _limit_text(WHITESPACE_PATTERN.sub(" ", safe).strip(), MAX_SHORT_TEXT_CHARS)


def _limit_text(value: str, max_chars: int) -> str:
    return value[:max_chars].strip()


def _read_limited(response) -> bytes:
    payload = bytearray()
    while True:
        chunk = response.read(DOWNLOAD_CHUNK_BYTES)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > MAX_PAGE_BYTES:
            raise ValueError(
                "openFDA Drugs@FDA response page exceeded the configured limit: "
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
            "openFDA Drugs@FDA request resolved to an unexpected host: "
            f"{hostname!r}. Allowed hosts: {', '.join(sorted(ALLOWED_DOWNLOAD_HOSTS))}"
        )
