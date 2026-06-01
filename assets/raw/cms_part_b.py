"""@bruin
name: raw.cms_part_b
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace
columns:
  - name: cms_part_b_hcpcs_key
    type: varchar
    description: Stable key built from the CMS Part B HCPCS code.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: source_year
    type: varchar
    description: Latest annual source year represented by this CMS file.
    checks:
      - name: not_null
  - name: hcpcs_code
    type: varchar
    description: CMS Healthcare Common Procedure Coding System code.
    checks:
      - name: not_null
  - name: hcpcs_description
    type: varchar
    description: CMS short description for the HCPCS drug code.
    checks:
      - name: not_null
  - name: brand_name_source
    type: varchar
    description: Original CMS Part B brand name text after whitespace normalization.
  - name: generic_name_source
    type: varchar
    description: Original CMS Part B generic name text after whitespace normalization.
  - name: brand_name
    type: varchar
    description: CMS Part B brand name with CMS asterisk markers removed.
  - name: generic_name
    type: varchar
    description: CMS Part B generic name with CMS asterisk markers removed.
  - name: brand_name_multiple_names_flag
    type: varchar
    description: Yes when CMS marks the brand field as representing multiple names.
    checks:
      - name: not_null
  - name: generic_name_multiple_names_flag
    type: varchar
    description: Yes when CMS marks the generic field as representing multiple names.
    checks:
      - name: not_null
  - name: brand_name_unavailable_flag
    type: varchar
    description: Yes when CMS marks the brand field as unavailable.
    checks:
      - name: not_null
  - name: generic_name_unavailable_flag
    type: varchar
    description: Yes when CMS marks the generic field as unavailable.
    checks:
      - name: not_null
  - name: brand_name_marker_stripped_flag
    type: varchar
    description: Yes when a trailing CMS marker was stripped from the brand field.
    checks:
      - name: not_null
  - name: generic_name_marker_stripped_flag
    type: varchar
    description: Yes when a trailing CMS marker was stripped from the generic field.
    checks:
      - name: not_null
  - name: has_usable_name
    type: varchar
    description: Yes when either cleaned brand or generic name remains usable for matching.
    checks:
      - name: not_null
  - name: total_spending_2019
    type: varchar
    description: 2019 aggregate Part B spending from Tot_Spndng_2019.
  - name: total_dosage_units_2019
    type: varchar
    description: 2019 total Part B dosage units.
  - name: total_claims_2019
    type: varchar
    description: 2019 total Part B claims.
  - name: total_beneficiaries_2019
    type: varchar
    description: 2019 total Part B beneficiaries.
  - name: avg_spending_per_dosage_unit_2019
    type: varchar
    description: 2019 average Part B spending per dosage unit.
  - name: avg_spending_per_claim_2019
    type: varchar
    description: 2019 average Part B spending per claim.
  - name: avg_spending_per_beneficiary_2019
    type: varchar
    description: 2019 average Part B spending per beneficiary.
  - name: outlier_flag_2019
    type: varchar
    description: 2019 CMS Part B outlier flag.
  - name: total_spending_2020
    type: varchar
    description: 2020 aggregate Part B spending from Tot_Spndng_2020.
  - name: total_dosage_units_2020
    type: varchar
    description: 2020 total Part B dosage units.
  - name: total_claims_2020
    type: varchar
    description: 2020 total Part B claims.
  - name: total_beneficiaries_2020
    type: varchar
    description: 2020 total Part B beneficiaries.
  - name: avg_spending_per_dosage_unit_2020
    type: varchar
    description: 2020 average Part B spending per dosage unit.
  - name: avg_spending_per_claim_2020
    type: varchar
    description: 2020 average Part B spending per claim.
  - name: avg_spending_per_beneficiary_2020
    type: varchar
    description: 2020 average Part B spending per beneficiary.
  - name: outlier_flag_2020
    type: varchar
    description: 2020 CMS Part B outlier flag.
  - name: total_spending_2021
    type: varchar
    description: 2021 aggregate Part B spending from Tot_Spndng_2021.
  - name: total_dosage_units_2021
    type: varchar
    description: 2021 total Part B dosage units.
  - name: total_claims_2021
    type: varchar
    description: 2021 total Part B claims.
  - name: total_beneficiaries_2021
    type: varchar
    description: 2021 total Part B beneficiaries.
  - name: avg_spending_per_dosage_unit_2021
    type: varchar
    description: 2021 average Part B spending per dosage unit.
  - name: avg_spending_per_claim_2021
    type: varchar
    description: 2021 average Part B spending per claim.
  - name: avg_spending_per_beneficiary_2021
    type: varchar
    description: 2021 average Part B spending per beneficiary.
  - name: outlier_flag_2021
    type: varchar
    description: 2021 CMS Part B outlier flag.
  - name: total_spending_2022
    type: varchar
    description: 2022 aggregate Part B spending from Tot_Spndng_2022.
  - name: total_dosage_units_2022
    type: varchar
    description: 2022 total Part B dosage units.
  - name: total_claims_2022
    type: varchar
    description: 2022 total Part B claims.
  - name: total_beneficiaries_2022
    type: varchar
    description: 2022 total Part B beneficiaries.
  - name: avg_spending_per_dosage_unit_2022
    type: varchar
    description: 2022 average Part B spending per dosage unit.
  - name: avg_spending_per_claim_2022
    type: varchar
    description: 2022 average Part B spending per claim.
  - name: avg_spending_per_beneficiary_2022
    type: varchar
    description: 2022 average Part B spending per beneficiary.
  - name: outlier_flag_2022
    type: varchar
    description: 2022 CMS Part B outlier flag.
  - name: total_spending_2023
    type: varchar
    description: 2023 aggregate Part B spending from Tot_Spndng_2023.
    checks:
      - name: not_null
  - name: total_dosage_units_2023
    type: varchar
    description: 2023 total Part B dosage units.
  - name: total_claims_2023
    type: varchar
    description: 2023 total Part B claims.
    checks:
      - name: not_null
  - name: total_beneficiaries_2023
    type: varchar
    description: 2023 total Part B beneficiaries. CMS may suppress this value on low-count rows.
  - name: avg_spending_per_dosage_unit_2023
    type: varchar
    description: 2023 average Part B spending per dosage unit.
  - name: avg_spending_per_claim_2023
    type: varchar
    description: 2023 average Part B spending per claim.
  - name: avg_spending_per_beneficiary_2023
    type: varchar
    description: 2023 average Part B spending per beneficiary.
  - name: outlier_flag_2023
    type: varchar
    description: 2023 CMS Part B outlier flag.
  - name: avg_asp_price_2023
    type: varchar
    description: Average 2023 ASP price reported by CMS.
  - name: change_avg_spending_per_dosage_unit_2022_2023
    type: varchar
    description: Change in average spending per dosage unit from 2022 to 2023.
  - name: cagr_avg_spending_per_dosage_unit_2019_2023
    type: varchar
    description: Annual growth rate in average spending per dosage unit from 2019 to 2023.

custom_checks:
  - name: CMS Part B HCPCS keys are unique
    query: select count(*) from (select cms_part_b_hcpcs_key from raw.cms_part_b group by 1 having count(*) > 1)
    value: 0
  - name: CMS Part B source year is accepted
    query: select count(*) from raw.cms_part_b where source_year <> '2023'
    value: 0
  - name: CMS Part B 2023 spending is nonnegative
    query: select count(*) from raw.cms_part_b where try_cast(total_spending_2023 as double) is null or try_cast(total_spending_2023 as double) < 0
    value: 0
  - name: CMS Part B 2023 claims and beneficiaries are nonnegative
    query: select count(*) from raw.cms_part_b where total_claims_2023 is null or try_cast(total_claims_2023 as double) is null or try_cast(total_claims_2023 as double) < 0 or (total_beneficiaries_2023 is not null and (try_cast(total_beneficiaries_2023 as double) is null or try_cast(total_beneficiaries_2023 as double) < 0))
    value: 0
  - name: CMS Part B name sentinels are not treated as drug names
    query: select count(*) from raw.cms_part_b where brand_name in ('*', '**') or generic_name in ('*', '**')
    value: 0
  - name: CMS Part B stripped marker rows retain source names
    query: select count(*) from raw.cms_part_b where (brand_name_marker_stripped_flag = 'Yes' and (brand_name_source is null or brand_name_source not like '%*' or brand_name_source in ('*', '**'))) or (generic_name_marker_stripped_flag = 'Yes' and (generic_name_source is null or generic_name_source not like '%*' or generic_name_source in ('*', '**')))
    value: 0
  - name: CMS Part B name flags use accepted values
    query: select count(*) from raw.cms_part_b where brand_name_multiple_names_flag not in ('Yes', 'No') or generic_name_multiple_names_flag not in ('Yes', 'No') or brand_name_unavailable_flag not in ('Yes', 'No') or generic_name_unavailable_flag not in ('Yes', 'No') or brand_name_marker_stripped_flag not in ('Yes', 'No') or generic_name_marker_stripped_flag not in ('Yes', 'No') or has_usable_name not in ('Yes', 'No')
    value: 0
  - name: CMS Part B HCPCS description is retained when names are unavailable
    query: select count(*) from raw.cms_part_b where has_usable_name = 'No' and coalesce(hcpcs_description, '') = ''
    value: 0
@bruin"""

from __future__ import annotations

import csv
import io
import re
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from urllib.parse import quote, urlparse

CMS_PART_B_LANDING_PAGE = (
    "https://data.cms.gov/summary-statistics-on-use-and-payments/"
    "medicare-medicaid-spending-by-drug/medicare-part-b-spending-by-drug"
)
CMS_PART_B_CSV_URL = (
    "https://data.cms.gov/sites/default/files/2025-05/"
    "f52d5fcd-8d93-481d-9173-6219813e4efb/"
    "DSD_PTB_RY25_P06_V10_DYT23_HCPCS-%20250430.csv"
)
CMS_PART_B_SOURCE_YEAR = "2023"
MAX_CSV_BYTES = 100 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
MAX_FIELD_CHARS = 5000
ALLOWED_DOWNLOAD_HOSTS = {"data.cms.gov"}
CSV_COMPATIBLE_CONTENT_TYPES = {"", "application/csv", "application/octet-stream", "text/csv", "text/plain"}
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]+")
WHITESPACE_PATTERN = re.compile(r"\s+")

CMS_PART_B_COLUMNS = {
    "HCPCS_Cd": "hcpcs_code",
    "HCPCS_Desc": "hcpcs_description",
    "Tot_Spndng_2019": "total_spending_2019",
    "Tot_Dsg_Unts_2019": "total_dosage_units_2019",
    "Tot_Clms_2019": "total_claims_2019",
    "Tot_Benes_2019": "total_beneficiaries_2019",
    "Avg_Spndng_Per_Dsg_Unt_2019": "avg_spending_per_dosage_unit_2019",
    "Avg_Spndng_Per_Clm_2019": "avg_spending_per_claim_2019",
    "Avg_Spndng_Per_Bene_2019": "avg_spending_per_beneficiary_2019",
    "Outlier_Flag_2019": "outlier_flag_2019",
    "Tot_Spndng_2020": "total_spending_2020",
    "Tot_Dsg_Unts_2020": "total_dosage_units_2020",
    "Tot_Clms_2020": "total_claims_2020",
    "Tot_Benes_2020": "total_beneficiaries_2020",
    "Avg_Spndng_Per_Dsg_Unt_2020": "avg_spending_per_dosage_unit_2020",
    "Avg_Spndng_Per_Clm_2020": "avg_spending_per_claim_2020",
    "Avg_Spndng_Per_Bene_2020": "avg_spending_per_beneficiary_2020",
    "Outlier_Flag_2020": "outlier_flag_2020",
    "Tot_Spndng_2021": "total_spending_2021",
    "Tot_Dsg_Unts_2021": "total_dosage_units_2021",
    "Tot_Clms_2021": "total_claims_2021",
    "Tot_Benes_2021": "total_beneficiaries_2021",
    "Avg_Spndng_Per_Dsg_Unt_2021": "avg_spending_per_dosage_unit_2021",
    "Avg_Spndng_Per_Clm_2021": "avg_spending_per_claim_2021",
    "Avg_Spndng_Per_Bene_2021": "avg_spending_per_beneficiary_2021",
    "Outlier_Flag_2021": "outlier_flag_2021",
    "Tot_Spndng_2022": "total_spending_2022",
    "Tot_Dsg_Unts_2022": "total_dosage_units_2022",
    "Tot_Clms_2022": "total_claims_2022",
    "Tot_Benes_2022": "total_beneficiaries_2022",
    "Avg_Spndng_Per_Dsg_Unt_2022": "avg_spending_per_dosage_unit_2022",
    "Avg_Spndng_Per_Clm_2022": "avg_spending_per_claim_2022",
    "Avg_Spndng_Per_Bene_2022": "avg_spending_per_beneficiary_2022",
    "Outlier_Flag_2022": "outlier_flag_2022",
    "Tot_Spndng_2023": "total_spending_2023",
    "Tot_Dsg_Unts_2023": "total_dosage_units_2023",
    "Tot_Clms_2023": "total_claims_2023",
    "Tot_Benes_2023": "total_beneficiaries_2023",
    "Avg_Spndng_Per_Dsg_Unt_2023": "avg_spending_per_dosage_unit_2023",
    "Avg_Spndng_Per_Clm_2023": "avg_spending_per_claim_2023",
    "Avg_Spndng_Per_Bene_2023": "avg_spending_per_beneficiary_2023",
    "Outlier_Flag_2023": "outlier_flag_2023",
    "Avg_DY23_ASP_Price": "avg_asp_price_2023",
    "Chg_Avg_Spndng_Per_Dsg_Unt_22_23": "change_avg_spending_per_dosage_unit_2022_2023",
    "CAGR_Avg_Spnd_Per_Dsg_Unt_19_23": "cagr_avg_spending_per_dosage_unit_2019_2023",
}

CMS_PART_B_SOURCE_COLUMNS = ("Brnd_Name", "Gnrc_Name", *CMS_PART_B_COLUMNS.keys())
CMS_PART_B_NUMERIC_COLUMNS = {
    source
    for source in CMS_PART_B_COLUMNS
    if source
    not in {
        "HCPCS_Cd",
        "HCPCS_Desc",
    }
}
REQUIRED_SOURCE_COLUMNS = ("HCPCS_Cd", "HCPCS_Desc", "Tot_Spndng_2023", "Tot_Clms_2023")


def materialize() -> list[dict[str, str | None]]:
    payload = _download_csv()
    text_file = io.StringIO(payload.decode("utf-8-sig"), newline="")
    reader = csv.DictReader(text_file)
    _validate_columns(reader.fieldnames or [], CMS_PART_B_SOURCE_COLUMNS)
    rows = [_rename_columns(row, source_row_number) for source_row_number, row in enumerate(reader, start=2)]
    _validate_unique_hcpcs_keys(rows)

    rows_without_usable_names = sum(1 for row in rows if row["has_usable_name"] == "No")
    rows_with_multiple_name_markers = sum(
        1
        for row in rows
        if row["brand_name_multiple_names_flag"] == "Yes"
        or row["generic_name_multiple_names_flag"] == "Yes"
    )
    stripped_marker_fields = sum(
        1
        for row in rows
        for flag in ("brand_name_marker_stripped_flag", "generic_name_marker_stripped_flag")
        if row[flag] == "Yes"
    )
    print(
        f"Loaded {len(rows):,} rows from CMS Part B annual {CMS_PART_B_SOURCE_YEAR} "
        f"via {CMS_PART_B_LANDING_PAGE} at {datetime.now(UTC).isoformat()}. "
        f"Rows with CMS multiple-name markers: {rows_with_multiple_name_markers:,}; "
        f"rows without usable names: {rows_without_usable_names:,}. "
        f"Warning: stripped trailing CMS name markers from {stripped_marker_fields:,} fields; "
        "original values retained in brand_name_source and generic_name_source."
    )
    return rows


def _download_csv() -> bytes:
    request = urllib.request.Request(
        CMS_PART_B_CSV_URL,
        headers={
            "Accept": "text/csv",
            "User-Agent": "Lapse CMS Part B ingestion",
        },
    )
    opener = urllib.request.build_opener(_AllowlistedRedirectHandler)
    with opener.open(request, timeout=120) as response:
        _validate_response_host(response.geturl())
        content_type = response.headers.get("Content-Type", "")
        content_length = response.headers.get("Content-Length")
        _validate_content_length(content_length)
        payload = _read_limited(response)

    if not _is_csv_compatible_content_type(content_type):
        raise ValueError(
            "CMS Part B download did not return a CSV-compatible content type. "
            f"Content-Type was {content_type!r}; source URL: {CMS_PART_B_CSV_URL}"
        )

    return payload


def _validate_content_length(content_length: str | None) -> None:
    if not content_length:
        return
    try:
        parsed_length = int(content_length)
    except ValueError:
        print(
            "CMS Part B response had a malformed Content-Length header; "
            "falling back to streaming size enforcement."
        )
        return
    if parsed_length > MAX_CSV_BYTES:
        raise ValueError(
            "CMS Part B CSV is larger than the configured limit: "
            f"{parsed_length} bytes > {MAX_CSV_BYTES} bytes"
        )


def _is_csv_compatible_content_type(content_type: str) -> bool:
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type in CSV_COMPATIBLE_CONTENT_TYPES


class _AllowlistedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_response_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _validate_response_host(url: str) -> None:
    hostname = urlparse(url).hostname
    if hostname not in ALLOWED_DOWNLOAD_HOSTS:
        raise ValueError(
            "CMS Part B download resolved to an unexpected host: "
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
                "CMS Part B CSV exceeded the configured download limit: "
                f"{len(payload)} bytes > {MAX_CSV_BYTES} bytes"
            )
    return bytes(payload)


def _validate_columns(actual_columns: list[str], expected_columns: Iterable[str]) -> None:
    missing = [column for column in expected_columns if column not in actual_columns]
    if missing:
        raise ValueError(
            "CMS Part B CSV is missing expected columns: "
            f"{', '.join(missing)}. Actual columns: {', '.join(actual_columns)}"
        )


def _rename_columns(row: dict[str, str], source_row_number: int) -> dict[str, str | None]:
    _validate_required_values(row, source_row_number)
    brand_source_name = _clean_text(row.get("Brnd_Name", ""))
    generic_source_name = _clean_text(row.get("Gnrc_Name", ""))
    brand_name, brand_multiple, brand_unavailable, brand_marker_stripped = _cms_name(brand_source_name)
    generic_name, generic_multiple, generic_unavailable, generic_marker_stripped = _cms_name(
        generic_source_name
    )
    renamed: dict[str, str | None] = {}
    for source, target in CMS_PART_B_COLUMNS.items():
        cleaned = _clean_text(row.get(source, ""))
        renamed[target] = None if source in CMS_PART_B_NUMERIC_COLUMNS and not cleaned else cleaned

    hcpcs_code = str(renamed["hcpcs_code"])
    renamed["cms_part_b_hcpcs_key"] = _hcpcs_key(hcpcs_code)
    renamed["source_year"] = CMS_PART_B_SOURCE_YEAR
    renamed["brand_name_source"] = brand_source_name
    renamed["generic_name_source"] = generic_source_name
    renamed["brand_name"] = brand_name
    renamed["generic_name"] = generic_name
    renamed["brand_name_multiple_names_flag"] = _yes_no(brand_multiple)
    renamed["generic_name_multiple_names_flag"] = _yes_no(generic_multiple)
    renamed["brand_name_unavailable_flag"] = _yes_no(brand_unavailable)
    renamed["generic_name_unavailable_flag"] = _yes_no(generic_unavailable)
    renamed["brand_name_marker_stripped_flag"] = _yes_no(brand_marker_stripped)
    renamed["generic_name_marker_stripped_flag"] = _yes_no(generic_marker_stripped)
    renamed["has_usable_name"] = _yes_no(bool(brand_name or generic_name))
    # Source text is returned as data for Bruin to materialize. Do not SQL-escape it here;
    # downstream consumers must use static SQL or parameterized queries, never string concatenation.
    return renamed


def _validate_required_values(row: dict[str, str], source_row_number: int) -> None:
    missing = [column for column in REQUIRED_SOURCE_COLUMNS if not _clean_text(row.get(column, ""))]
    if missing:
        raise ValueError(
            "CMS Part B row is missing required values at source row "
            f"{source_row_number}: {', '.join(missing)}"
        )


def _cms_name(value: object) -> tuple[str, bool, bool, bool]:
    text = _clean_text(value)
    if text == "**":
        return "", False, True, False
    if text == "*":
        return "", True, False, False
    if _has_trailing_cms_multiple_marker(text):
        cleaned = text[:-1].rstrip()
        return cleaned, True, False, True
    return text, False, False, False


def _has_trailing_cms_multiple_marker(text: str) -> bool:
    return text.endswith("*") and text not in {"*", "**"} and text.count("*") == 1


def _hcpcs_key(hcpcs_code: str) -> str:
    component = quote(hcpcs_code, safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")
    return f"HCPCS{len(component)}:{component}"


def _validate_unique_hcpcs_keys(rows: Iterable[dict[str, str | None]]) -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        key = row["cms_part_b_hcpcs_key"]
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    if duplicates:
        duplicate_list = ", ".join(sorted(duplicates)[:10])
        raise ValueError(f"CMS Part B HCPCS keys are not unique: {duplicate_list}")


def _clean_text(value: object) -> str:
    without_controls = CONTROL_CHARACTER_PATTERN.sub(" ", _text(value))
    normalized = WHITESPACE_PATTERN.sub(" ", without_controls).strip()
    if len(normalized) > MAX_FIELD_CHARS:
        raise ValueError(
            "CMS Part B field exceeded the configured text limit: "
            f"{len(normalized)} characters > {MAX_FIELD_CHARS} characters"
        )
    return normalized


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
