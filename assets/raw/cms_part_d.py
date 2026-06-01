"""@bruin
name: raw.cms_part_d
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace
columns:
  - name: brand_name
    type: varchar
    description: CMS Part D brand name.
  - name: generic_name
    type: varchar
    description: CMS Part D generic name.
  - name: total_manufacturers
    type: varchar
    description: Number of manufacturers CMS reports for this drug row.
  - name: manufacturer_name
    type: varchar
    description: Manufacturer name, or Overall for aggregate rows.
  - name: total_spending_2019
    type: varchar
    description: 2019 total Part D spending.
  - name: total_dosage_units_2019
    type: varchar
    description: 2019 total dosage units.
  - name: total_claims_2019
    type: varchar
    description: 2019 total claims.
  - name: total_beneficiaries_2019
    type: varchar
    description: 2019 total beneficiaries.
  - name: avg_spending_per_dosage_unit_weighted_2019
    type: varchar
    description: 2019 weighted average spending per dosage unit.
  - name: avg_spending_per_claim_2019
    type: varchar
    description: 2019 average spending per claim.
  - name: avg_spending_per_beneficiary_2019
    type: varchar
    description: 2019 average spending per beneficiary.
  - name: outlier_flag_2019
    type: varchar
    description: 2019 CMS outlier flag.
  - name: total_spending_2020
    type: varchar
    description: 2020 total Part D spending.
  - name: total_dosage_units_2020
    type: varchar
    description: 2020 total dosage units.
  - name: total_claims_2020
    type: varchar
    description: 2020 total claims.
  - name: total_beneficiaries_2020
    type: varchar
    description: 2020 total beneficiaries.
  - name: avg_spending_per_dosage_unit_weighted_2020
    type: varchar
    description: 2020 weighted average spending per dosage unit.
  - name: avg_spending_per_claim_2020
    type: varchar
    description: 2020 average spending per claim.
  - name: avg_spending_per_beneficiary_2020
    type: varchar
    description: 2020 average spending per beneficiary.
  - name: outlier_flag_2020
    type: varchar
    description: 2020 CMS outlier flag.
  - name: total_spending_2021
    type: varchar
    description: 2021 total Part D spending.
  - name: total_dosage_units_2021
    type: varchar
    description: 2021 total dosage units.
  - name: total_claims_2021
    type: varchar
    description: 2021 total claims.
  - name: total_beneficiaries_2021
    type: varchar
    description: 2021 total beneficiaries.
  - name: avg_spending_per_dosage_unit_weighted_2021
    type: varchar
    description: 2021 weighted average spending per dosage unit.
  - name: avg_spending_per_claim_2021
    type: varchar
    description: 2021 average spending per claim.
  - name: avg_spending_per_beneficiary_2021
    type: varchar
    description: 2021 average spending per beneficiary.
  - name: outlier_flag_2021
    type: varchar
    description: 2021 CMS outlier flag.
  - name: total_spending_2022
    type: varchar
    description: 2022 total Part D spending.
  - name: total_dosage_units_2022
    type: varchar
    description: 2022 total dosage units.
  - name: total_claims_2022
    type: varchar
    description: 2022 total claims.
  - name: total_beneficiaries_2022
    type: varchar
    description: 2022 total beneficiaries.
  - name: avg_spending_per_dosage_unit_weighted_2022
    type: varchar
    description: 2022 weighted average spending per dosage unit.
  - name: avg_spending_per_claim_2022
    type: varchar
    description: 2022 average spending per claim.
  - name: avg_spending_per_beneficiary_2022
    type: varchar
    description: 2022 average spending per beneficiary.
  - name: outlier_flag_2022
    type: varchar
    description: 2022 CMS outlier flag.
  - name: total_spending_2023
    type: varchar
    description: 2023 total Part D spending.
  - name: total_dosage_units_2023
    type: varchar
    description: 2023 total dosage units.
  - name: total_claims_2023
    type: varchar
    description: 2023 total claims.
  - name: total_beneficiaries_2023
    type: varchar
    description: 2023 total beneficiaries.
  - name: avg_spending_per_dosage_unit_weighted_2023
    type: varchar
    description: 2023 weighted average spending per dosage unit.
  - name: avg_spending_per_claim_2023
    type: varchar
    description: 2023 average spending per claim.
  - name: avg_spending_per_beneficiary_2023
    type: varchar
    description: 2023 average spending per beneficiary.
  - name: outlier_flag_2023
    type: varchar
    description: 2023 CMS outlier flag.
  - name: change_avg_spending_per_dosage_unit_2022_2023
    type: varchar
    description: Change in average spending per dosage unit from 2022 to 2023.
  - name: cagr_avg_spending_per_dosage_unit_2019_2023
    type: varchar
    description: Annual growth rate in average spending per dosage unit from 2019 to 2023.
  - name: source_year
    type: varchar
    description: Latest annual source year represented by this CMS file.
@bruin"""

from __future__ import annotations

import csv
import io
import urllib.request
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

CMS_PART_D_LANDING_PAGE = (
    "https://data.cms.gov/summary-statistics-on-use-and-payments/"
    "medicare-medicaid-spending-by-drug/medicare-part-d-spending-by-drug"
)
CMS_PART_D_CSV_URL = (
    "https://data.cms.gov/sites/default/files/2025-05/"
    "56d95a8b-138c-4b60-84a5-613fbab7197f/"
    "DSD_PTD_RY25_P04_V10_DY23_BGM.csv"
)
CMS_PART_D_SOURCE_YEAR = "2023"
MAX_CSV_BYTES = 100 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
ALLOWED_DOWNLOAD_HOSTS = {"data.cms.gov"}
CSV_COMPATIBLE_CONTENT_TYPES = {"", "application/csv", "application/octet-stream", "text/csv", "text/plain"}
SPREADSHEET_FORMULA_PREFIXES = ("=", "+", "-", "@")

CMS_PART_D_COLUMNS = {
    "Brnd_Name": "brand_name",
    "Gnrc_Name": "generic_name",
    "Tot_Mftr": "total_manufacturers",
    "Mftr_Name": "manufacturer_name",
    "Tot_Spndng_2019": "total_spending_2019",
    "Tot_Dsg_Unts_2019": "total_dosage_units_2019",
    "Tot_Clms_2019": "total_claims_2019",
    "Tot_Benes_2019": "total_beneficiaries_2019",
    "Avg_Spnd_Per_Dsg_Unt_Wghtd_2019": "avg_spending_per_dosage_unit_weighted_2019",
    "Avg_Spnd_Per_Clm_2019": "avg_spending_per_claim_2019",
    "Avg_Spnd_Per_Bene_2019": "avg_spending_per_beneficiary_2019",
    "Outlier_Flag_2019": "outlier_flag_2019",
    "Tot_Spndng_2020": "total_spending_2020",
    "Tot_Dsg_Unts_2020": "total_dosage_units_2020",
    "Tot_Clms_2020": "total_claims_2020",
    "Tot_Benes_2020": "total_beneficiaries_2020",
    "Avg_Spnd_Per_Dsg_Unt_Wghtd_2020": "avg_spending_per_dosage_unit_weighted_2020",
    "Avg_Spnd_Per_Clm_2020": "avg_spending_per_claim_2020",
    "Avg_Spnd_Per_Bene_2020": "avg_spending_per_beneficiary_2020",
    "Outlier_Flag_2020": "outlier_flag_2020",
    "Tot_Spndng_2021": "total_spending_2021",
    "Tot_Dsg_Unts_2021": "total_dosage_units_2021",
    "Tot_Clms_2021": "total_claims_2021",
    "Tot_Benes_2021": "total_beneficiaries_2021",
    "Avg_Spnd_Per_Dsg_Unt_Wghtd_2021": "avg_spending_per_dosage_unit_weighted_2021",
    "Avg_Spnd_Per_Clm_2021": "avg_spending_per_claim_2021",
    "Avg_Spnd_Per_Bene_2021": "avg_spending_per_beneficiary_2021",
    "Outlier_Flag_2021": "outlier_flag_2021",
    "Tot_Spndng_2022": "total_spending_2022",
    "Tot_Dsg_Unts_2022": "total_dosage_units_2022",
    "Tot_Clms_2022": "total_claims_2022",
    "Tot_Benes_2022": "total_beneficiaries_2022",
    "Avg_Spnd_Per_Dsg_Unt_Wghtd_2022": "avg_spending_per_dosage_unit_weighted_2022",
    "Avg_Spnd_Per_Clm_2022": "avg_spending_per_claim_2022",
    "Avg_Spnd_Per_Bene_2022": "avg_spending_per_beneficiary_2022",
    "Outlier_Flag_2022": "outlier_flag_2022",
    "Tot_Spndng_2023": "total_spending_2023",
    "Tot_Dsg_Unts_2023": "total_dosage_units_2023",
    "Tot_Clms_2023": "total_claims_2023",
    "Tot_Benes_2023": "total_beneficiaries_2023",
    "Avg_Spnd_Per_Dsg_Unt_Wghtd_2023": "avg_spending_per_dosage_unit_weighted_2023",
    "Avg_Spnd_Per_Clm_2023": "avg_spending_per_claim_2023",
    "Avg_Spnd_Per_Bene_2023": "avg_spending_per_beneficiary_2023",
    "Outlier_Flag_2023": "outlier_flag_2023",
    "Chg_Avg_Spnd_Per_Dsg_Unt_22_23": "change_avg_spending_per_dosage_unit_2022_2023",
    "CAGR_Avg_Spnd_Per_Dsg_Unt_19_23": "cagr_avg_spending_per_dosage_unit_2019_2023",
}


def materialize() -> list[dict[str, str]]:
    payload = _download_csv()
    text_file = io.StringIO(payload.decode("utf-8-sig"), newline="")
    reader = csv.DictReader(text_file)
    _validate_columns(reader.fieldnames or [], CMS_PART_D_COLUMNS.keys())
    rows = [_rename_columns(row) for row in reader]

    print(
        f"Loaded {len(rows):,} rows from CMS Part D annual {CMS_PART_D_SOURCE_YEAR} "
        f"via {CMS_PART_D_LANDING_PAGE} at {datetime.now(UTC).isoformat()}"
    )
    return rows


def _download_csv() -> bytes:
    request = urllib.request.Request(
        CMS_PART_D_CSV_URL,
        headers={
            "Accept": "text/csv",
            "User-Agent": "Lapse CMS Part D ingestion",
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
            "CMS Part D download did not return a CSV-compatible content type. "
            f"Content-Type was {content_type!r}; source URL: {CMS_PART_D_CSV_URL}"
        )

    return payload


def _validate_content_length(content_length: str | None) -> None:
    if not content_length:
        return
    try:
        parsed_length = int(content_length)
    except ValueError:
        print(
            "CMS Part D response had a malformed Content-Length header; "
            "falling back to streaming size enforcement."
        )
        return
    if parsed_length > MAX_CSV_BYTES:
        raise ValueError(
            "CMS Part D CSV is larger than the configured limit: "
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
            "CMS Part D download resolved to an unexpected host: "
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
                "CMS Part D CSV exceeded the configured download limit: "
                f"{len(payload)} bytes > {MAX_CSV_BYTES} bytes"
            )
    return bytes(payload)


def _validate_columns(actual_columns: list[str], expected_columns: Iterable[str]) -> None:
    missing = [column for column in expected_columns if column not in actual_columns]
    if missing:
        raise ValueError(
            "CMS Part D CSV is missing expected columns: "
            f"{', '.join(missing)}. Actual columns: {', '.join(actual_columns)}"
        )


def _rename_columns(row: dict[str, str]) -> dict[str, str]:
    renamed = {
        target: _spreadsheet_safe(row.get(source, ""))
        for source, target in CMS_PART_D_COLUMNS.items()
    }
    renamed["source_year"] = CMS_PART_D_SOURCE_YEAR
    return renamed


def _spreadsheet_safe(value: str) -> str:
    trimmed = value.lstrip()
    if not trimmed.startswith(SPREADSHEET_FORMULA_PREFIXES):
        return value
    if trimmed[0] in {"+", "-"} and _looks_numeric(trimmed):
        return value
    return f"'{value}"


def _looks_numeric(value: str) -> bool:
    try:
        Decimal(value)
    except InvalidOperation:
        return False
    return True
