/* @bruin
name: staging.cms_orange_book_match_diagnostics
type: duckdb.sql
materialization:
  type: table

depends:
  - staging.drug_revenue
  - staging.cms_orange_book_matches

columns:
  - name: diagnostic_key
    type: varchar
    description: Single-row diagnostics key.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: cms_drug_count
    type: integer
    description: Number of normalized CMS aggregate drug rows.
  - name: matched_cms_drug_count
    type: integer
    description: Number of CMS drug rows with at least one Orange Book NDA match.
  - name: unmatched_cms_drug_count
    type: integer
    description: Number of CMS drug rows without an Orange Book NDA match.
  - name: cms_match_rate_pct
    type: decimal
    description: Share of CMS drug rows with at least one Orange Book NDA match.
  - name: cms_drugs_with_multiple_applications
    type: integer
    description: Count of CMS drug rows matching more than one NDA application.
  - name: max_applications_per_cms_drug
    type: integer
    description: Highest number of matched NDA applications for any one CMS drug.
  - name: total_match_candidate_rows
    type: integer
    description: Total CMS-to-application candidate rows in staging.cms_orange_book_matches.

custom_checks:
  - name: diagnostics emits exactly one row
    query: select count(*) from staging.cms_orange_book_match_diagnostics
    value: 1
  - name: matched plus unmatched equals CMS total
    query: select count(*) from staging.cms_orange_book_match_diagnostics where matched_cms_drug_count + unmatched_cms_drug_count <> cms_drug_count
    value: 0
  - name: match rate is a percentage
    query: select count(*) from staging.cms_orange_book_match_diagnostics where cms_match_rate_pct < 0 or cms_match_rate_pct > 100
    value: 0
  - name: fanout metrics are populated
    query: select count(*) from staging.cms_orange_book_match_diagnostics where cms_drugs_with_multiple_applications is null or max_applications_per_cms_drug is null
    value: 0
@bruin */

with per_cms_drug as (
    select
        revenue.cms_drug_key,
        count(distinct matches.appl_no) as matched_application_count
    from staging.drug_revenue as revenue
    left join staging.cms_orange_book_matches as matches
        on revenue.cms_drug_key = matches.cms_drug_key
    group by revenue.cms_drug_key
),
summary as (
    select
        count(*) as cms_drug_count,
        count(*) filter (where matched_application_count > 0) as matched_cms_drug_count,
        count(*) filter (where matched_application_count = 0) as unmatched_cms_drug_count,
        count(*) filter (where matched_application_count > 1) as cms_drugs_with_multiple_applications,
        max(matched_application_count) as max_applications_per_cms_drug,
        sum(matched_application_count) as total_match_candidate_rows
    from per_cms_drug
)
select
    'cms_orange_book_match_summary' as diagnostic_key,
    cms_drug_count,
    matched_cms_drug_count,
    unmatched_cms_drug_count,
    cast(round(100.0 * matched_cms_drug_count / nullif(cms_drug_count, 0), 2) as decimal(5, 2)) as cms_match_rate_pct,
    cms_drugs_with_multiple_applications,
    max_applications_per_cms_drug,
    total_match_candidate_rows
from summary;
