"""@bruin
name: raw.purple_book
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace
columns:
  - name: purple_book_product_key
    type: varchar
    description: Stable key built from BLA number and Purple Book product number.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: source_release
    type: varchar
    description: Purple Book monthly release represented by this raw download.
    checks:
      - name: not_null
  - name: source_row_number
    type: integer
    description: One-based CSV row number in the downloaded file for traceability.
    checks:
      - name: not_null
  - name: monthly_update_code
    type: varchar
    description: FDA monthly change code when present; N=new, R=added in release, U=updated.
  - name: applicant
    type: varchar
    description: FDA applicant or sponsor.
    checks:
      - name: not_null
  - name: bla_number
    type: varchar
    description: FDA Biologics License Application number.
    checks:
      - name: not_null
  - name: proprietary_name
    type: varchar
    description: Proprietary or brand name as provided by the Purple Book.
  - name: proper_name
    type: varchar
    description: Proper or nonproprietary biological product name.
    checks:
      - name: not_null
  - name: license_type
    type: varchar
    description: FDA license type, including 351(a), 351(k) Biosimilar, and 351(k) Interchangeable.
    checks:
      - name: not_null
  - name: biosimilar_interchangeable_status
    type: varchar
    description: Derived status used downstream for biologic competition grouping.
    checks:
      - name: not_null
  - name: is_reference_product
    type: varchar
    description: Yes when the row is a 351(a) product in the Purple Book.
    checks:
      - name: not_null
  - name: is_biosimilar
    type: varchar
    description: Yes when the row is licensed under 351(k).
    checks:
      - name: not_null
  - name: is_interchangeable
    type: varchar
    description: Yes when FDA lists the row as 351(k) Interchangeable.
    checks:
      - name: not_null
  - name: reference_product_group_key
    type: varchar
    description: Percent-encoded uppercase grouping key connecting 351(k) rows to their reference product.
    checks:
      - name: not_null
  - name: strength
    type: varchar
    description: Product strength.
  - name: dosage_form
    type: varchar
    description: Dosage form.
  - name: route_of_administration
    type: varchar
    description: Route of administration.
  - name: product_presentation
    type: varchar
    description: Product presentation.
  - name: marketing_status
    type: varchar
    description: Purple Book marketing status.
    checks:
      - name: not_null
  - name: licensure
    type: varchar
    description: Licensure status.
    checks:
      - name: not_null
  - name: withdrawn_flag
    type: varchar
    description: Yes when the product is discontinued or the license is revoked.
    checks:
      - name: not_null
  - name: approval_date
    type: varchar
    description: Raw FDA approval date text.
  - name: interchangeable_approval_date
    type: varchar
    description: Raw FDA interchangeable approval date text.
  - name: reference_product_proper_name
    type: varchar
    description: Proper name of the reference product for 351(k) rows.
  - name: reference_product_proprietary_name
    type: varchar
    description: Proprietary name of the reference product for 351(k) rows.
  - name: supplement_number
    type: varchar
    description: Supplement number as provided by the Purple Book.
  - name: submission_type
    type: varchar
    description: FDA submission type.
  - name: interchangeable_supplement_number
    type: varchar
    description: Interchangeable supplement number as provided by the Purple Book.
  - name: license_number
    type: varchar
    description: FDA license number.
  - name: product_number
    type: varchar
    description: Purple Book product number within the BLA.
    checks:
      - name: not_null
  - name: center
    type: varchar
    description: FDA center, usually CDER or CBER.
    checks:
      - name: not_null
  - name: date_of_first_licensure
    type: varchar
    description: Raw date of first licensure text.
  - name: exclusivity_expiration_date
    type: varchar
    description: Raw exclusivity expiration date text.
  - name: first_interchangeable_exclusivity_expiration_date
    type: varchar
    description: Raw first interchangeable exclusivity expiration date text.
  - name: reference_product_exclusivity_expiration_date
    type: varchar
    description: Raw reference-product exclusivity expiration date text.
  - name: orphan_exclusivity_expiration_date
    type: varchar
    description: Raw orphan exclusivity expiration date text.
  - name: patent_list_provided
    type: varchar
    description: Whether FDA reports that a patent list was provided.

custom_checks:
  - name: Purple Book product keys are unique
    query: select count(*) from (select purple_book_product_key from raw.purple_book group by 1 having count(*) > 1)
    value: 0
  - name: reference products are present
    query: select case when count(*) > 0 then 0 else 1 end from raw.purple_book where is_reference_product = 'Yes'
    value: 0
  - name: biosimilar or interchangeable products are present
    query: select case when count(*) > 0 then 0 else 1 end from raw.purple_book where is_biosimilar = 'Yes'
    value: 0
  - name: 351k rows have reference product grouping
    query: select count(*) from raw.purple_book where is_biosimilar = 'Yes' and (reference_product_group_key is null or reference_product_group_key = '')
    value: 0
  - name: Purple Book license types use accepted values
    query: select count(*) from raw.purple_book where license_type not in ('351(a)', '351(k) Biosimilar', '351(k) Interchangeable')
    value: 0
  - name: Purple Book derived statuses use accepted values
    query: select count(*) from raw.purple_book where biosimilar_interchangeable_status not in ('reference_product', 'biosimilar', 'interchangeable')
    value: 0
  - name: Purple Book yes no flags use accepted values
    query: select count(*) from raw.purple_book where is_reference_product not in ('Yes', 'No') or is_biosimilar not in ('Yes', 'No') or is_interchangeable not in ('Yes', 'No') or withdrawn_flag not in ('Yes', 'No')
    value: 0
  - name: Purple Book group key encodes pipe delimiters
    query: select count(*) from raw.purple_book where reference_product_group_key like '%|%'
    value: 0
  - name: Purple Book date fields parse when populated
    query: select count(*) from raw.purple_book where (lower(trim(approval_date)) not in ('', 'date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown') and try_strptime(trim(approval_date), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) is null) or (lower(trim(interchangeable_approval_date)) not in ('', 'date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown') and try_strptime(trim(interchangeable_approval_date), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) is null) or (lower(trim(date_of_first_licensure)) not in ('', 'date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown') and try_strptime(trim(date_of_first_licensure), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) is null) or (lower(trim(exclusivity_expiration_date)) not in ('', 'date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown') and try_strptime(trim(exclusivity_expiration_date), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) is null) or (lower(trim(first_interchangeable_exclusivity_expiration_date)) not in ('', 'date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown') and try_strptime(trim(first_interchangeable_exclusivity_expiration_date), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) is null) or (lower(trim(reference_product_exclusivity_expiration_date)) not in ('', 'date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown') and try_strptime(trim(reference_product_exclusivity_expiration_date), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) is null) or (lower(trim(orphan_exclusivity_expiration_date)) not in ('', 'date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown') and try_strptime(trim(orphan_exclusivity_expiration_date), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) is null)
    value: 0
@bruin"""

from __future__ import annotations

import csv
import io
import os
import re
import time
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse

PURPLE_BOOK_DOWNLOAD_PAGE = "https://purplebooksearch.fda.gov/downloads"
PURPLE_BOOK_CSV_URL_ENV_VAR = "LAPSE_PURPLE_BOOK_CSV_URL"
PURPLE_BOOK_SOURCE_RELEASE_ENV_VAR = "LAPSE_PURPLE_BOOK_SOURCE_RELEASE"
MAX_CSV_BYTES = 25 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
ALLOWED_DOWNLOAD_HOSTS = {"purplebooksearch.fda.gov", "www.accessdata.fda.gov"}
CSV_COMPATIBLE_CONTENT_TYPES = {"", "application/csv", "application/octet-stream", "text/csv", "text/plain"}
HTML_COMPATIBLE_CONTENT_TYPES = {"", "text/html"}
MAX_FIELD_CHARS = 5000
MISSING_VALUE_SENTINELS = {
    "",
    "DATE TBD",
    "N/A",
    "NA",
    "NOT APPLICABLE",
    "NOT AVAILABLE",
    "NOT PROVIDED",
    "PENDING",
    "TBD",
    "UNKNOWN",
}
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")
WHITESPACE_PATTERN = re.compile(r"\s+")
PURPLE_BOOK_CSV_URL_PATTERN = re.compile(
    r"/PurpleBook/(?P<year>[0-9]{4})/purplebook-search-(?P<month>[A-Za-z]+)-data-download[.]csv$",
    re.IGNORECASE,
)
MONTH_NUMBERS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

PURPLE_BOOK_COLUMNS = {
    "N/R/U": "monthly_update_code",
    "Applicant": "applicant",
    "BLA Number": "bla_number",
    "Proprietary Name": "proprietary_name",
    "Proper Name": "proper_name",
    "License Type": "license_type",
    "Strength": "strength",
    "Dosage Form": "dosage_form",
    "Route of Administration": "route_of_administration",
    "Product Presentation": "product_presentation",
    "Marketing Status": "marketing_status",
    "Licensure": "licensure",
    "Approval Date": "approval_date",
    "Inter. Approval Date": "interchangeable_approval_date",
    "Ref. Product Proper Name": "reference_product_proper_name",
    "Ref. Product Proprietary Name": "reference_product_proprietary_name",
    "Supplement Number": "supplement_number",
    "Submission Type": "submission_type",
    "Inter. Supplement Number": "interchangeable_supplement_number",
    "License Number": "license_number",
    "Product Number": "product_number",
    "Center": "center",
    "Date of First Licensure": "date_of_first_licensure",
    "Exclusivity Expiration Date": "exclusivity_expiration_date",
    "First Interchangeable Exclusivity Exp. Date": "first_interchangeable_exclusivity_expiration_date",
    "Ref. Product Exclusivity Exp. Date": "reference_product_exclusivity_expiration_date",
    "Orphan Exclusivity Exp. Date": "orphan_exclusivity_expiration_date",
    "Patent List Provided": "patent_list_provided",
}


def materialize() -> list[dict[str, str | int]]:
    csv_url, source_release = _resolve_source()
    payload = _download_csv(csv_url)
    source_rows = _extract_all_products_table(payload)
    rows = [
        _rename_row(row, source_row_number, source_release)
        for source_row_number, row in source_rows
    ]
    _validate_required_values(rows)
    _validate_unique_product_keys(rows)

    print(
        f"Loaded {len(rows):,} Purple Book product rows from {source_release} "
        f"via {PURPLE_BOOK_DOWNLOAD_PAGE} at {datetime.now(UTC).isoformat()}"
    )
    return rows


def _resolve_source() -> tuple[str, str]:
    configured_url = _text(os.environ.get(PURPLE_BOOK_CSV_URL_ENV_VAR))
    configured_release = _text(os.environ.get(PURPLE_BOOK_SOURCE_RELEASE_ENV_VAR))
    if configured_url:
        _validate_response_host(configured_url)
        return configured_url, configured_release or _release_from_url(configured_url) or "custom"

    source_page = _download_source_page()
    candidates = _extract_csv_candidates(source_page)
    if not candidates:
        raise ValueError(
            "FDA Purple Book downloads page did not expose any CSV downloads. "
            f"Set {PURPLE_BOOK_CSV_URL_ENV_VAR} to an official CSV URL to override discovery."
        )

    latest = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))
    _year, _month_number, release, csv_url = latest
    return csv_url, configured_release or release


def _download_source_page() -> str:
    payload = _download_url(
        PURPLE_BOOK_DOWNLOAD_PAGE,
        accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        compatible_content_types=HTML_COMPATIBLE_CONTENT_TYPES,
    )
    return payload.decode("utf-8", errors="replace")


def _extract_csv_candidates(html: str) -> list[tuple[int, int, str, str]]:
    parser = _LinkParser()
    parser.feed(html)

    candidates = []
    for href in parser.hrefs:
        csv_url = urljoin(PURPLE_BOOK_DOWNLOAD_PAGE, href)
        parsed = _parse_purple_book_csv_url(csv_url)
        if parsed is None:
            continue
        year, month_number, release = parsed
        _validate_response_host(csv_url)
        candidates.append((year, month_number, release, csv_url))

    return candidates


def _parse_purple_book_csv_url(url: str) -> tuple[int, int, str] | None:
    match = PURPLE_BOOK_CSV_URL_PATTERN.search(urlparse(url).path)
    if match is None:
        return None

    month = match.group("month").lower()
    month_number = MONTH_NUMBERS.get(month)
    if month_number is None:
        return None

    year = int(match.group("year"))
    release = f"{month.title()} {year}"
    return year, month_number, release


def _release_from_url(url: str) -> str:
    parsed = _parse_purple_book_csv_url(url)
    if parsed is None:
        return ""
    _year, _month_number, release = parsed
    return release


def _download_csv(csv_url: str) -> bytes:
    payload = _download_url(
        csv_url,
        accept="text/csv,application/octet-stream,*/*",
        compatible_content_types=CSV_COMPATIBLE_CONTENT_TYPES,
    )
    return payload


def _download_url(url: str, accept: str, compatible_content_types: set[str]) -> bytes:
    _validate_response_host(url)
    opener = urllib.request.build_opener(_AllowlistedRedirectHandler)

    for attempt in range(MAX_RETRIES + 1):
        request = urllib.request.Request(
            url,
            headers={
                "Accept": accept,
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                ),
            },
        )
        try:
            with opener.open(request, timeout=120) as response:
                _validate_response_host(response.geturl())
                content_type = response.headers.get("Content-Type", "")
                content_length = response.headers.get("Content-Length")
                _validate_content_length(content_length)
                payload = _read_limited(response)
            if not _is_compatible_content_type(content_type, compatible_content_types):
                raise ValueError(
                    "FDA Purple Book download did not return an expected content type. "
                    f"Content-Type was {content_type!r}; source URL: {url}"
                )
            return payload
        except HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS_CODES or attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "FDA Purple Book download failed with HTTP status "
                    f"{exc.code}; request URL redacted"
                ) from None
            time.sleep(2**attempt)
        except URLError as exc:
            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    f"FDA Purple Book download failed after retries: {exc.reason}"
                ) from None
            time.sleep(2**attempt)

    raise RuntimeError("FDA Purple Book download retry loop exited unexpectedly")


def _extract_all_products_table(payload: bytes) -> list[tuple[int, dict[str, str]]]:
    text_file = io.StringIO(payload.decode("utf-8-sig"), newline="")
    reader = csv.reader(text_file)
    raw_rows = list(reader)
    header_indexes = [
        index for index, row in enumerate(raw_rows) if _trimmed_row(row) == list(PURPLE_BOOK_COLUMNS)
    ]

    if len(header_indexes) < 2:
        raise ValueError(
            "FDA Purple Book CSV did not contain the expected monthly-change and all-products "
            f"tables. Found {len(header_indexes)} matching headers."
        )

    header_index = header_indexes[-1]
    header = _trimmed_row(raw_rows[header_index])
    _validate_columns(header)

    rows: list[tuple[int, dict[str, str]]] = []
    for index, row in enumerate(raw_rows[header_index + 1 :], start=header_index + 2):
        if not any(_text(cell) for cell in row):
            continue
        values = _trimmed_row(row)
        if values == list(PURPLE_BOOK_COLUMNS):
            raise ValueError(
                "FDA Purple Book CSV contained an unexpected repeated header after the "
                f"all-products table at source row {index}."
            )
        if len(values) != len(header):
            raise ValueError(
                "FDA Purple Book CSV row width changed at source row "
                f"{index}: {len(values)} fields != {len(header)} expected fields"
            )
        rows.append((index, dict(zip(header, row, strict=True))))

    if not rows:
        raise ValueError("FDA Purple Book all-products table did not contain any product rows.")

    return rows


def _validate_columns(actual_columns: list[str]) -> None:
    expected_columns = list(PURPLE_BOOK_COLUMNS)
    if actual_columns != expected_columns:
        raise ValueError(
            "FDA Purple Book CSV header changed. Expected columns: "
            f"{', '.join(expected_columns)}. Actual columns: {', '.join(actual_columns)}"
        )


def _rename_row(
    source: dict[str, str],
    source_row_number: int,
    source_release: str,
) -> dict[str, str | int]:
    row = {
        target: _clean_text(source.get(source_column, ""))
        for source_column, target in PURPLE_BOOK_COLUMNS.items()
    }
    row["source_release"] = source_release
    row["source_row_number"] = source_row_number
    row["purple_book_product_key"] = _product_key(
        row["bla_number"],
        row["product_number"],
    )
    row["biosimilar_interchangeable_status"] = _biosimilar_interchangeable_status(row["license_type"])
    row["is_reference_product"] = _yes_no(row["license_type"] == "351(a)")
    row["is_biosimilar"] = _yes_no(row["license_type"].startswith("351(k)"))
    row["is_interchangeable"] = _yes_no(row["license_type"] == "351(k) Interchangeable")
    row["withdrawn_flag"] = _yes_no(_is_withdrawn(row["marketing_status"], row["licensure"]))
    row["reference_product_group_key"] = _reference_product_group_key(source, row["license_type"])
    return row


def _product_key(bla_number: str, product_number: str) -> str:
    bla_component = _key_component(bla_number)
    product_component = _key_component(product_number)
    return (
        f"BLA{len(bla_component)}:{bla_component}|"
        f"PRODUCT{len(product_component)}:{product_component}"
    )


def _key_component(value: str) -> str:
    return quote(str(value), safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")


def _biosimilar_interchangeable_status(license_type: str) -> str:
    if license_type == "351(k) Interchangeable":
        return "interchangeable"
    if license_type == "351(k) Biosimilar":
        return "biosimilar"
    if license_type == "351(a)":
        return "reference_product"
    return "unknown"


def _reference_product_group_key(source: dict[str, str], license_type: str | int) -> str:
    if str(license_type).startswith("351(k)"):
        proper_name = _source_group_key_text(source.get("Ref. Product Proper Name", ""))
        proprietary_name = _source_group_key_text(source.get("Ref. Product Proprietary Name", ""))
    else:
        proper_name = _source_group_key_text(source.get("Proper Name", ""))
        proprietary_name = _source_group_key_text(source.get("Proprietary Name", ""))

    key_parts = [
        _length_prefixed_key_component(label, value)
        for label, value in (("PROPER", proper_name), ("PROPRIETARY", proprietary_name))
        if value
    ]
    return "".join(key_parts)


def _source_group_key_text(value: object) -> str:
    return _source_missing_to_blank(_clean_text(value))


def _length_prefixed_key_component(label: str, value: str) -> str:
    component = _key_component(value.upper())
    return f"{label}{len(component)}:{component}"


def _source_missing_to_blank(value: object) -> str:
    text = _text(value)
    if text.strip().upper() in MISSING_VALUE_SENTINELS:
        return ""
    return text


def _is_withdrawn(marketing_status: str, licensure: str) -> bool:
    normalized_marketing_status = marketing_status.casefold()
    normalized_licensure = licensure.casefold()
    return normalized_marketing_status.startswith("disc") or normalized_licensure in {
        "revoked",
        "voluntarily revoked",
    }


def _validate_required_values(rows: Iterable[dict[str, str | int]]) -> None:
    required_fields = (
        "applicant",
        "bla_number",
        "proper_name",
        "license_type",
        "product_number",
        "center",
        "marketing_status",
        "licensure",
    )
    for row in rows:
        missing = [field for field in required_fields if not _text(row.get(field))]
        if missing:
            source_row_number = row.get("source_row_number", "unknown")
            raise ValueError(
                "FDA Purple Book row is missing required values at source row "
                f"{source_row_number}: {', '.join(missing)}"
            )


def _validate_unique_product_keys(rows: Iterable[dict[str, str | int]]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        product_key = str(row["purple_book_product_key"])
        if product_key in seen:
            duplicates.add(product_key)
        seen.add(product_key)
    if duplicates:
        raise ValueError(
            "FDA Purple Book product keys are not unique: "
            f"{', '.join(sorted(duplicates)[:10])}"
        )


def _validate_content_length(content_length: str | None) -> None:
    if not content_length:
        return
    try:
        parsed_length = int(content_length)
    except ValueError:
        print(
            "FDA Purple Book response had a malformed Content-Length header; "
            "falling back to streaming size enforcement."
        )
        return
    if parsed_length > MAX_CSV_BYTES:
        raise ValueError(
            "FDA Purple Book CSV is larger than the configured limit: "
            f"{parsed_length} bytes > {MAX_CSV_BYTES} bytes"
        )


def _is_compatible_content_type(content_type: str, compatible_content_types: set[str]) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type in compatible_content_types


class _AllowlistedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_response_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_response_host(url: str) -> None:
    hostname = urlparse(url).hostname
    if hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError(
            "FDA Purple Book download resolved to an unexpected host: "
            f"{hostname!r}. Allowed hosts: {', '.join(sorted(ALLOWED_DOWNLOAD_HOSTS))}"
        )


def _read_limited(response) -> bytes:
    payload = bytearray()
    while True:
        chunk = response.read(DOWNLOAD_CHUNK_BYTES)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > MAX_CSV_BYTES:
            raise ValueError(
                "FDA Purple Book CSV exceeded the configured download limit: "
                f"{len(payload)} bytes > {MAX_CSV_BYTES} bytes"
            )
    return bytes(payload)


def _trimmed_row(row: Iterable[str]) -> list[str]:
    return [_clean_text(value) for value in row]


def _clean_text(value: object) -> str:
    without_controls = CONTROL_CHARACTER_PATTERN.sub(" ", _text(value))
    normalized = WHITESPACE_PATTERN.sub(" ", without_controls).strip()
    if len(normalized) > MAX_FIELD_CHARS:
        raise ValueError(
            "FDA Purple Book field exceeded the configured text limit: "
            f"{len(normalized)} characters > {MAX_FIELD_CHARS} characters"
        )
    return normalized


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for attr_name, attr_value in attrs:
            if attr_name.lower() == "href" and attr_value:
                self.hrefs.append(attr_value)
