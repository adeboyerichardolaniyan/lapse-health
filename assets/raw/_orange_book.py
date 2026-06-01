from __future__ import annotations

import csv
import io
import urllib.request
import zipfile
from collections.abc import Iterable
from datetime import UTC, datetime

ORANGE_BOOK_DATA_PAGE = (
    "https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files"
)
ORANGE_BOOK_ZIP_URL = "https://www.fda.gov/media/76860/download?attachment="
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_ZIP_ENTRIES = 10
MAX_MEMBER_BYTES = 25 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 1024 * 1024

PRODUCT_COLUMNS = {
    "Ingredient": "ingredient",
    "DF;Route": "df_route",
    "Trade_Name": "trade_name",
    "Applicant": "applicant",
    "Strength": "strength",
    "Appl_Type": "appl_type",
    "Appl_No": "appl_no",
    "Product_No": "product_no",
    "TE_Code": "te_code",
    "Approval_Date": "approval_date",
    "RLD": "rld",
    "RS": "rs",
    "Type": "type",
    "Applicant_Full_Name": "applicant_full_name",
}

PATENT_COLUMNS = {
    "Appl_Type": "appl_type",
    "Appl_No": "appl_no",
    "Product_No": "product_no",
    "Patent_No": "patent_no",
    "Patent_Expire_Date_Text": "patent_expire_date_text",
    "Drug_Substance_Flag": "drug_substance_flag",
    "Drug_Product_Flag": "drug_product_flag",
    "Patent_Use_Code": "patent_use_code",
    "Delist_Flag": "delist_flag",
    "Submission_Date": "submission_date",
}

EXCLUSIVITY_COLUMNS = {
    "Appl_Type": "appl_type",
    "Appl_No": "appl_no",
    "Product_No": "product_no",
    "Exclusivity_Code": "exclusivity_code",
    "Exclusivity_Date": "exclusivity_date",
}


def read_orange_book_file(
    source_filename: str,
    expected_columns: dict[str, str],
) -> list[dict[str, str]]:
    archive_bytes = _download_archive()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        _validate_archive_shape(archive)
        member = _find_member(archive.namelist(), source_filename)
        _validate_member_size(archive, member)
        with archive.open(member) as raw_file:
            text_file = io.TextIOWrapper(raw_file, encoding="latin-1", newline="")
            reader = csv.DictReader(text_file, delimiter="~")
            _validate_columns(
                filename=member,
                actual_columns=reader.fieldnames or [],
                expected_columns=expected_columns.keys(),
            )
            rows = [_rename_columns(row, expected_columns) for row in reader]

    print(
        f"Loaded {len(rows):,} rows from {source_filename} via "
        f"{ORANGE_BOOK_DATA_PAGE} at {datetime.now(UTC).isoformat()}"
    )
    return rows


def _download_archive() -> bytes:
    request = urllib.request.Request(
        ORANGE_BOOK_ZIP_URL,
        headers={
            "Accept": "application/zip",
            "User-Agent": "Lapse Orange Book ingestion",
        },
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        content_type = response.headers.get("Content-Type", "")
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
            raise ValueError(
                "FDA Orange Book ZIP is larger than the configured limit: "
                f"{content_length} bytes > {MAX_ARCHIVE_BYTES} bytes"
            )
        payload = _read_limited(response)

    if not zipfile.is_zipfile(io.BytesIO(payload)):
        raise ValueError(
            "FDA Orange Book download did not return a ZIP archive. "
            f"Content-Type was {content_type!r}; source URL: {ORANGE_BOOK_ZIP_URL}"
        )

    return payload


def _read_limited(response) -> bytes:
    payload = bytearray()
    while True:
        chunk = response.read(DOWNLOAD_CHUNK_BYTES)
        if not chunk:
            break
        payload.extend(chunk)
        if len(payload) > MAX_ARCHIVE_BYTES:
            raise ValueError(
                "FDA Orange Book ZIP exceeded the configured download limit: "
                f"{len(payload)} bytes > {MAX_ARCHIVE_BYTES} bytes"
            )
    return bytes(payload)


def _validate_archive_shape(archive: zipfile.ZipFile) -> None:
    members = archive.infolist()
    if len(members) > MAX_ZIP_ENTRIES:
        raise ValueError(
            "FDA Orange Book ZIP contains more files than expected: "
            f"{len(members)} entries > {MAX_ZIP_ENTRIES} entries"
        )


def _validate_member_size(archive: zipfile.ZipFile, member: str) -> None:
    file_size = archive.getinfo(member).file_size
    if file_size > MAX_MEMBER_BYTES:
        raise ValueError(
            f"{member} is larger than the configured extraction limit: "
            f"{file_size} bytes > {MAX_MEMBER_BYTES} bytes"
        )


def _find_member(members: Iterable[str], expected_filename: str) -> str:
    expected = expected_filename.lower()
    for member in members:
        if member.lower() == expected:
            return member

    available = ", ".join(sorted(members))
    raise ValueError(
        f"FDA Orange Book ZIP is missing {expected_filename!r}. "
        f"Available files: {available}"
    )


def _validate_columns(
    filename: str,
    actual_columns: list[str],
    expected_columns: Iterable[str],
) -> None:
    missing = [column for column in expected_columns if column not in actual_columns]
    if missing:
        raise ValueError(
            f"{filename} is missing expected columns: {', '.join(missing)}. "
            f"Actual columns: {', '.join(actual_columns)}"
        )


def _rename_columns(
    row: dict[str, str],
    column_map: dict[str, str],
) -> dict[str, str]:
    return {target: row.get(source, "") for source, target in column_map.items()}
