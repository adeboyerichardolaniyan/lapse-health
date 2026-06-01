/* @bruin
name: staging.cms_part_b_biologic_match_diagnostics
type: duckdb.sql
materialization:
  type: table

depends:
  - staging.drug_revenue
  - staging.cms_part_b_biologic_matches

columns:
  - name: diagnostic_key
    type: varchar
    description: Single-row diagnostics key.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: cms_part_b_drug_count
    type: integer
    description: Number of normalized CMS drug rows with Part B spending.
  - name: matched_cms_part_b_drug_count
    type: integer
    description: Number of Part B CMS drug rows with at least one Purple Book reference biologic match.
  - name: unmatched_cms_part_b_drug_count
    type: integer
    description: Number of Part B CMS drug rows without a Purple Book reference biologic match.
  - name: cms_part_b_match_rate_pct
    type: decimal
    description: Share of Part B CMS drug rows with at least one Purple Book reference biologic match.
  - name: cms_part_b_drugs_with_multiple_biologic_matches
    type: integer
    description: Count of Part B CMS drug rows matching more than one reference biologic.
  - name: max_biologic_matches_per_cms_part_b_drug
    type: integer
    description: Highest number of reference biologic matches for any one Part B CMS drug.
  - name: total_match_candidate_rows
    type: integer
    description: Total Part B CMS-to-reference-biologic candidate rows.

custom_checks:
  - name: Part B biologic diagnostics emits exactly one row
    query: select count(*) from staging.cms_part_b_biologic_match_diagnostics
    value: 1
  - name: matched plus unmatched equals Part B CMS total
    query: select count(*) from staging.cms_part_b_biologic_match_diagnostics where matched_cms_part_b_drug_count + unmatched_cms_part_b_drug_count <> cms_part_b_drug_count
    value: 0
  - name: Part B biologic match rate is a percentage
    query: select count(*) from staging.cms_part_b_biologic_match_diagnostics where cms_part_b_match_rate_pct < 0 or cms_part_b_match_rate_pct > 100
    value: 0
  - name: Part B biologic fanout metrics are populated
    query: select count(*) from staging.cms_part_b_biologic_match_diagnostics where cms_part_b_drugs_with_multiple_biologic_matches is null or max_biologic_matches_per_cms_part_b_drug is null
    value: 0
@bruin */

with per_cms_part_b_drug as (
    select
        revenue.cms_drug_key,
        count(distinct matches.biologic_product_key) as matched_biologic_count
    from staging.drug_revenue as revenue
    left join staging.cms_part_b_biologic_matches as matches
        on revenue.cms_drug_key = matches.cms_drug_key
    where revenue.part_b_total_spending_2023 > 0
    group by revenue.cms_drug_key
),
summary as (
    select
        count(*) as cms_part_b_drug_count,
        count(*) filter (where matched_biologic_count > 0) as matched_cms_part_b_drug_count,
        count(*) filter (where matched_biologic_count = 0) as unmatched_cms_part_b_drug_count,
        count(*) filter (where matched_biologic_count > 1) as cms_part_b_drugs_with_multiple_biologic_matches,
        max(matched_biologic_count) as max_biologic_matches_per_cms_part_b_drug,
        sum(matched_biologic_count) as total_match_candidate_rows
    from per_cms_part_b_drug
)
select
    'cms_part_b_biologic_match_summary' as diagnostic_key,
    cms_part_b_drug_count,
    matched_cms_part_b_drug_count,
    unmatched_cms_part_b_drug_count,
    cast(round(100.0 * matched_cms_part_b_drug_count / nullif(cms_part_b_drug_count, 0), 2) as decimal(5, 2)) as cms_part_b_match_rate_pct,
    cms_part_b_drugs_with_multiple_biologic_matches,
    max_biologic_matches_per_cms_part_b_drug,
    total_match_candidate_rows
from summary;
