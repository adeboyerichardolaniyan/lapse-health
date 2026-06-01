"""@bruin
name: marts.site_opportunities
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace

depends:
  - marts.drug_opportunities
  - staging.drug_descriptions

columns:
  - name: id
    type: varchar
    description: Stable UI row identifier matching marts.drug_opportunities.opportunity_key.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: rank
    type: integer
    description: Opportunity rank from the source mart.
    checks:
      - name: not_null
      - name: unique
  - name: name
    type: varchar
    description: Decoded display drug name.
    checks:
      - name: not_null
  - name: drug_modality
    type: varchar
    description: Opportunity modality.
    checks:
      - name: not_null
  - name: opportunity_score
    type: decimal
    description: Source mart opportunity score, unchanged by export or enrichment.
    checks:
      - name: not_null
  - name: market_size_score
    type: decimal
    description: Source mart market-size component score.
  - name: timing_score
    type: decimal
    description: Source mart timing component score.
  - name: competition_score
    type: decimal
    description: Source mart competition-density component score.
  - name: market_size_usd
    type: decimal
    description: Matched annual Medicare market size.
  - name: months_to_window
    type: integer
    description: Months until the opportunity window opens, or negative months since expiry.
  - name: window_label
    type: varchar
    description: UI-ready deterministic timing label.
  - name: filer_count
    type: integer
    description: Generic ANDA application count for small molecules or biosimilar product count for biologics.
  - name: why
    type: varchar
    description: Export-time deterministic reason line used by the site detail panel.
  - name: drug_class
    type: varchar
    description: Optional openFDA label drug class.
  - name: mechanism
    type: varchar
    description: Optional openFDA label mechanism class.
  - name: description
    type: varchar
    description: Optional openFDA first-sentence or first-clause description.

custom_checks:
  - name: exported opportunity scores match source mart
    query: select count(*) from marts.site_opportunities as exported inner join marts.drug_opportunities as source on exported.id = source.opportunity_key where abs(cast(exported.opportunity_score as double) - cast(source.opportunity_score as double)) > 0.001
    value: 0
  - name: exported modalities are accepted
    query: select count(*) from marts.site_opportunities where drug_modality not in ('small_molecule', 'biologic')
    value: 0
  - name: exported UI text is constrained
    query: select count(*) from marts.site_opportunities where regexp_matches(coalesce(name, '') || coalesce(window_label, '') || coalesce(why, '') || coalesce(drug_class, '') || coalesce(mechanism, '') || coalesce(description, ''), '[^A-Za-z0-9,.;:()/%+ -]') or length(coalesce(name, '')) > 200 or length(coalesce(window_label, '')) > 80 or length(coalesce(why, '')) > 120 or length(coalesce(description, '')) > 260
    value: 0
  - name: exported names are display cased
    query: select count(*) from marts.site_opportunities where regexp_matches(name, '[A-Z]{4,}') and not regexp_matches(name, '[a-z]')
    value: 0
  - name: exported nullable text rejects placeholders
    query: select count(*) from marts.site_opportunities where lower(trim(coalesce(drug_class, ''))) in ('nan', 'null', 'none', 'n/a', 'na') or lower(trim(coalesce(mechanism, ''))) in ('nan', 'null', 'none', 'n/a', 'na') or lower(trim(coalesce(description, ''))) in ('nan', 'null', 'none', 'n/a', 'na')
    value: 0
  - name: exported descriptions contain letters
    query: select count(*) from marts.site_opportunities where description is not null and not regexp_matches(description, '[A-Za-z]')
    value: 0
@bruin"""

from __future__ import annotations

import base64
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from bruin import query

EXPORT_LIMIT = 50
SITE_DATA_PATH = Path(__file__).resolve().parents[2] / "site" / "data" / "opportunities.json"
BOUNDED_TEXT_PATTERN = re.compile(r"^DATA START ([A-Za-z0-9+/=]+) DATA END$")
CONTROL_CHARACTER_PATTERN = re.compile(r"[\x00-\x1f\x7f]+")
UNSAFE_UI_TEXT_PATTERN = re.compile(r"[^A-Za-z0-9,.;:()/%+ \-]+")
WHITESPACE_PATTERN = re.compile(r"\s+")
NAME_SEPARATOR_PATTERN = re.compile(r"([/-])")
PLACEHOLDER_TEXT_PATTERN = re.compile(r"[\s./_-]+")
DISPLAY_NAME_ACRONYMS = {
    "CD",
    "CR",
    "DR",
    "ER",
    "HFA",
    "IM",
    "IR",
    "IV",
    "LA",
    "ODT",
    "SC",
    "SQ",
    "SR",
    "XL",
    "XR",
}


def materialize() -> list[dict[str, Any]]:
    rows = _source_rows()
    exported = [_export_row(row) for row in rows]
    _write_site_json(exported)
    print(f"Wrote {len(exported):,} real opportunity rows to {SITE_DATA_PATH}")
    return exported


def _source_rows() -> list[dict[str, Any]]:
    frame = query(
        f"""
        select
            opportunities.opportunity_key as id,
            opportunities.opportunity_rank as rank,
            opportunities.primary_trade_name as encoded_name,
            opportunities.drug_modality,
            opportunities.opportunity_score,
            opportunities.market_size_score,
            opportunities.timing_score,
            opportunities.competition_density_score as competition_score,
            opportunities.total_market_spending_2023 as market_size_usd,
            opportunities.months_until_last_protection as months_to_window,
            case
                when opportunities.drug_modality = 'small_molecule'
                    then opportunities.matched_anda_application_count
                else opportunities.biosimilar_product_count
            end as filer_count,
            descriptions.drug_class,
            descriptions.mechanism,
            descriptions.description,
            opportunities.cms_source_year
        from marts.drug_opportunities as opportunities
        left join staging.drug_descriptions as descriptions
            on opportunities.opportunity_key = descriptions.opportunity_key
        order by opportunities.opportunity_rank
        limit {EXPORT_LIMIT}
        """
    )
    return frame.to_dict("records")


def _export_row(row: dict[str, Any]) -> dict[str, Any]:
    row_id = str(row["id"])
    months = _int_or_none(row.get("months_to_window"))
    market_size_score = _float_or_none(row.get("market_size_score"))
    timing_score = _float_or_none(row.get("timing_score"))
    competition_score = _float_or_none(row.get("competition_score"))
    filer_count = _int_or_zero(row.get("filer_count"))
    modality = str(row["drug_modality"])
    return {
        "id": row_id,
        "rank": _required_int(row.get("rank"), "rank", row_id),
        "name": _display_name(row.get("encoded_name")),
        "drug_modality": modality,
        "opportunity_score": _required_float(row.get("opportunity_score"), "opportunity_score", row_id),
        "market_size_score": market_size_score,
        "timing_score": timing_score,
        "competition_score": competition_score,
        "market_size_usd": _float_or_none(row.get("market_size_usd")),
        "months_to_window": months,
        "window_label": _window_label(months),
        "filer_count": filer_count,
        "why": _why_line(modality, market_size_score, timing_score, competition_score, filer_count),
        "drug_class": _nullable_text(row.get("drug_class"), 160),
        "mechanism": _nullable_text(row.get("mechanism"), 160),
        "description": _nullable_text(row.get("description"), 260),
    }


def _write_site_json(rows: list[dict[str, Any]]) -> None:
    modality_counts = {
        "small_molecule": sum(1 for row in rows if row["drug_modality"] == "small_molecule"),
        "biologic": sum(1 for row in rows if row["drug_modality"] == "biologic"),
    }
    source_year = _source_year()
    doc = {
        "_meta": {
            "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source_year": source_year,
            "sample": False,
            "schema_version": 3,
            "note": "Real pipeline export from marts.site_opportunities.",
            "enrichment_source": "openFDA Drug Labeling API (class / mechanism / indication blurb)",
            "modality_counts": modality_counts,
            "row_count": len(rows),
        },
        "opportunities": rows,
    }
    SITE_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SITE_DATA_PATH.write_text(json.dumps(doc, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _source_year() -> int | None:
    frame = query("select max(cms_source_year) as source_year from marts.drug_opportunities")
    value = frame.to_dict("records")[0]["source_year"]
    return _int_or_none(value)


def _why_line(
    modality: str,
    market_size_score: float | None,
    timing_score: float | None,
    competition_score: float | None,
    filer_count: int,
) -> str:
    competition_label = "biosimilars" if modality == "biologic" else "generics"
    if timing_score is not None and timing_score >= 80 and competition_score is not None and competition_score < 40:
        return f"Window is near, but {competition_label} crowding"
    if market_size_score is not None and market_size_score >= 90 and timing_score is not None and timing_score >= 80:
        return "Blockbuster market, near-term window"
    if competition_score is not None and competition_score >= 90 and filer_count == 0:
        return f"No {competition_label} yet"
    if market_size_score is not None and market_size_score >= 90 and timing_score is not None and timing_score < 55:
        return "Blockbuster market, but expiry is distant"
    if timing_score is not None and timing_score >= 90:
        return "Near-term window"
    if market_size_score is not None and market_size_score >= 70:
        return "Large market"
    if competition_score is not None and competition_score >= 80:
        return f"Open {competition_label} field"
    return "Watchlist opportunity"


def _window_label(months: int | None) -> str:
    if months is None:
        return "Unknown window"
    if months < 0:
        elapsed = abs(months)
        if elapsed < 13:
            return f"Expired {elapsed} mo ago"
        years = max(1, round(elapsed / 12))
        return f"Expired {years}yr ago"
    if months == 0:
        return "Opens now"
    if months <= 18:
        return f"Opens in {months} mo"
    now = datetime.now(UTC)
    year = now.year + ((now.month + months - 1) // 12)
    return f"Opens {year}" if months <= 60 else f"Opens {year} (distant)"


def _decode_bounded_text(value: object) -> str:
    text = _text(value)
    match = BOUNDED_TEXT_PATTERN.match(text)
    if not match:
        return text
    try:
        return base64.b64decode(match.group(1)).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return text


def _nullable_text(value: object, max_chars: int) -> str | None:
    text = _ui_safe_text(value, max_chars)
    if PLACEHOLDER_TEXT_PATTERN.sub("", text).lower() in {"nan", "null", "none", "na"}:
        return None
    return text or None


def _display_name(value: object) -> str:
    text = _ui_safe_text(_decode_bounded_text(value), 200)
    if not text or any(char.islower() for char in text):
        return text
    return " ".join(_display_name_word(word) for word in text.split())


def _display_name_word(word: str) -> str:
    return "".join(
        part if index % 2 else _display_name_part(part)
        for index, part in enumerate(NAME_SEPARATOR_PATTERN.split(word))
    )


def _display_name_part(value: str) -> str:
    if value.upper() in DISPLAY_NAME_ACRONYMS or not any(char.isalpha() for char in value):
        return value.upper()
    return value[0].upper() + value[1:].lower()


def _ui_safe_text(value: object, max_chars: int) -> str:
    without_controls = CONTROL_CHARACTER_PATTERN.sub(" ", _text(value))
    safe = UNSAFE_UI_TEXT_PATTERN.sub(" ", without_controls)
    return WHITESPACE_PATTERN.sub(" ", safe).strip()[:max_chars].strip()


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _required_float(value: object, field: str, row_id: str) -> float:
    parsed = _float_or_none(value)
    if parsed is None:
        raise ValueError(f"Cannot export opportunity {row_id}: required {field} is null")
    return parsed


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _required_int(value: object, field: str, row_id: str) -> int:
    parsed = _int_or_none(value)
    if parsed is None:
        raise ValueError(f"Cannot export opportunity {row_id}: required {field} is null")
    return parsed


def _int_or_zero(value: object) -> int:
    parsed = _int_or_none(value)
    return parsed if parsed is not None else 0


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
