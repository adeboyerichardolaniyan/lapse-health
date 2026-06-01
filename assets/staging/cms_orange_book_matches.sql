/* @bruin
name: staging.cms_orange_book_matches
type: duckdb.sql
materialization:
  type: table

depends:
  - staging.drug_revenue
  - staging.branded_drugs

columns:
  - name: cms_drug_application_key
    type: varchar
    description: Stable key for a CMS drug to Orange Book application candidate match.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: cms_drug_key
    type: varchar
    description: CMS drug key from staging.drug_revenue.
    checks:
      - name: not_null
  - name: appl_no
    type: varchar
    description: Candidate FDA NDA application number matched by normalized brand name.
    checks:
      - name: not_null
  - name: matched_product_count
    type: integer
    description: Number of NDA product rows supporting this candidate match.
  - name: generic_aligned_product_count
    type: integer
    description: Number of matched products whose ingredient key also matches CMS generic key.
  - name: match_quality
    type: varchar
    description: brand_and_generic when at least one product also matches generic ingredient; otherwise brand_only.
  - name: cms_brand_name
    type: varchar
    description: CMS brand name for the candidate.
  - name: cms_generic_name
    type: varchar
    description: CMS generic name for the candidate.
  - name: matched_trade_names
    type: varchar
    description: Orange Book trade names supporting the candidate.
  - name: matched_ingredients
    type: varchar
    description: Orange Book ingredient texts supporting the candidate.

custom_checks:
  - name: match candidate keys are unique
    query: select count(*) from (select cms_drug_application_key from staging.cms_orange_book_matches group by 1 having count(*) > 1)
    value: 0
  - name: matched product counts are positive
    query: select count(*) from staging.cms_orange_book_matches where matched_product_count <= 0
    value: 0
  - name: match quality uses accepted values
    query: select count(*) from staging.cms_orange_book_matches where match_quality not in ('brand_and_generic', 'brand_only')
    value: 0
@bruin */

with candidate_matches as (
    select
        revenue.cms_drug_key,
        drugs.appl_no,
        count(distinct drugs.branded_product_key) as matched_product_count,
        count(distinct case
            when drugs.ingredient_key = revenue.generic_name_key then drugs.branded_product_key
        end) as generic_aligned_product_count,
        revenue.brand_name as cms_brand_name,
        revenue.generic_name as cms_generic_name,
        string_agg(distinct drugs.trade_name, '; ' order by drugs.trade_name) as matched_trade_names,
        string_agg(distinct drugs.ingredient, '; ' order by drugs.ingredient) as matched_ingredients
    from staging.drug_revenue as revenue
    inner join staging.branded_drugs as drugs
        on revenue.brand_name_key = drugs.trade_name_key
    group by
        revenue.cms_drug_key,
        drugs.appl_no,
        revenue.brand_name,
        revenue.generic_name
)
select
    concat(cms_drug_key, '|', appl_no) as cms_drug_application_key,
    cms_drug_key,
    appl_no,
    matched_product_count,
    generic_aligned_product_count,
    case
        when generic_aligned_product_count > 0 then 'brand_and_generic'
        else 'brand_only'
    end as match_quality,
    cms_brand_name,
    cms_generic_name,
    matched_trade_names,
    matched_ingredients
from candidate_matches;
