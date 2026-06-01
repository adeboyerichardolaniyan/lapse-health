/* @bruin
name: staging.cms_part_b_biologic_matches
type: duckdb.sql
materialization:
  type: table

depends:
  - staging.drug_revenue
  - staging.biologic_products

columns:
  - name: cms_part_b_biologic_match_key
    type: varchar
    description: Stable key for a Part B CMS drug to Purple Book reference biologic candidate match.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: cms_drug_key
    type: varchar
    description: Normalized CMS drug key from staging.drug_revenue.
    checks:
      - name: not_null
  - name: biologic_product_key
    type: varchar
    description: Reference biologic key from staging.biologic_products.
    checks:
      - name: not_null
  - name: match_quality
    type: varchar
    description: brand_and_proper, brand, or proper match between CMS Part B and Purple Book names.
    checks:
      - name: not_null
  - name: cms_brand_name
    type: varchar
    description: Base64 encoded DATA START/END bounded CMS Part B brand names represented by the normalized CMS drug row.
  - name: cms_generic_name
    type: varchar
    description: Base64 encoded DATA START/END bounded CMS Part B generic names represented by the normalized CMS drug row.
  - name: biologic_proprietary_names
    type: varchar
    description: Base64 encoded DATA START/END bounded Purple Book proprietary names represented by the matched biologic group.
  - name: biologic_proper_name
    type: varchar
    description: Base64 encoded DATA START/END bounded Purple Book proper names represented by the matched biologic group.

custom_checks:
  - name: Part B biologic match candidate keys are unique
    query: select count(*) from (select cms_part_b_biologic_match_key from staging.cms_part_b_biologic_matches group by 1 having count(*) > 1)
    value: 0
  - name: Part B biologic match qualities are accepted
    query: select count(*) from staging.cms_part_b_biologic_matches where match_quality not in ('brand_and_proper', 'brand', 'proper')
    value: 0
  - name: Part B biologic matches are supported by Part B spend
    query: select count(*) from staging.cms_part_b_biologic_matches as matches left join staging.drug_revenue as revenue on matches.cms_drug_key = revenue.cms_drug_key where revenue.part_b_total_spending_2023 <= 0 or revenue.part_b_total_spending_2023 is null
    value: 0
  - name: AI-facing Part B biologic match text is data bounded
    query: select count(*) from staging.cms_part_b_biologic_matches where (cms_brand_name is not null and (not regexp_matches(cms_brand_name, '^DATA START [A-Za-z0-9+/=]+ DATA END$') or length(cms_brand_name) > 2000)) or (cms_generic_name is not null and (not regexp_matches(cms_generic_name, '^DATA START [A-Za-z0-9+/=]+ DATA END$') or length(cms_generic_name) > 2000)) or (biologic_proprietary_names is not null and (not regexp_matches(biologic_proprietary_names, '^DATA START [A-Za-z0-9+/=]+ DATA END$') or length(biologic_proprietary_names) > 2000)) or (biologic_proper_name is not null and (not regexp_matches(biologic_proper_name, '^DATA START [A-Za-z0-9+/=]+ DATA END$') or length(biologic_proper_name) > 2000))
    value: 0
@bruin */

with part_b_revenue as (
    select
        cms_drug_key,
        brand_name,
        brand_name_key,
        generic_name,
        generic_name_key
    from staging.drug_revenue
    where part_b_total_spending_2023 > 0
),
biologic_name_keys as (
    select
        biologic_product_key,
        'proper' as name_key_type,
        nullif(
            trim(lower(regexp_replace(regexp_replace(coalesce(name_parts.name_part, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))),
            ''
        ) as name_key
    from staging.biologic_products
    cross join unnest(string_split(coalesce(proper_name, ''), ',')) as name_parts(name_part)
    union
    select
        biologic_products.biologic_product_key,
        'brand' as name_key_type,
        nullif(
            trim(lower(regexp_replace(regexp_replace(coalesce(name_parts.name_part, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))),
            ''
        ) as name_key
    from staging.biologic_products as biologic_products
    cross join unnest(string_split(coalesce(biologic_products.proprietary_names, ''), ',')) as name_parts(name_part)
),
candidate_matches as (
    select
        part_b_revenue.cms_drug_key,
        biologic_products.biologic_product_key,
        part_b_revenue.brand_name as cms_brand_name,
        part_b_revenue.generic_name as cms_generic_name,
        biologic_products.proprietary_names as biologic_proprietary_names,
        biologic_products.proper_name as biologic_proper_name,
        max(case
            when biologic_name_keys.name_key_type = 'brand'
                and part_b_revenue.brand_name_key = biologic_name_keys.name_key then 1
            else 0
        end) as brand_matched,
        max(case
            when biologic_name_keys.name_key_type = 'proper'
                and part_b_revenue.generic_name_key = biologic_name_keys.name_key then 1
            else 0
        end) as proper_matched
    from part_b_revenue
    inner join biologic_name_keys
        on (
            biologic_name_keys.name_key_type = 'brand'
            and part_b_revenue.brand_name_key = biologic_name_keys.name_key
        )
        or (
            biologic_name_keys.name_key_type = 'proper'
            and part_b_revenue.generic_name_key = biologic_name_keys.name_key
        )
    inner join staging.biologic_products as biologic_products
        on biologic_name_keys.biologic_product_key = biologic_products.biologic_product_key
    where biologic_name_keys.name_key is not null
    group by
        part_b_revenue.cms_drug_key,
        biologic_products.biologic_product_key,
        part_b_revenue.brand_name,
        part_b_revenue.generic_name,
        biologic_products.proprietary_names,
        biologic_products.proper_name
),
safe_matches as (
    select
        cms_drug_key,
        biologic_product_key,
        case
            when brand_matched = 1 and proper_matched = 1 then 'brand_and_proper'
            when brand_matched = 1 then 'brand'
            else 'proper'
        end as match_quality,
        coalesce(
            nullif(
                left(trim(regexp_replace(regexp_replace(coalesce(cms_brand_name, ''), '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                ''
            ),
            'unsupported text'
        ) as cms_brand_name,
        coalesce(
            nullif(
                left(trim(regexp_replace(regexp_replace(coalesce(cms_generic_name, ''), '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                ''
            ),
            'unsupported text'
        ) as cms_generic_name,
        case
            when biologic_proprietary_names is null then null
            else coalesce(
                nullif(
                    left(trim(regexp_replace(regexp_replace(biologic_proprietary_names, '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 2000),
                    ''
                ),
                'unsupported text'
            )
        end as biologic_proprietary_names,
        coalesce(
            nullif(
                left(trim(regexp_replace(regexp_replace(coalesce(biologic_proper_name, ''), '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                ''
            ),
            'unsupported text'
        ) as biologic_proper_name
    from candidate_matches
)
select
    concat(cms_drug_key, '|', biologic_product_key) as cms_part_b_biologic_match_key,
    cms_drug_key,
    biologic_product_key,
    match_quality,
    concat('DATA START ', base64(cast(left(cms_brand_name, 1485) as blob)), ' DATA END') as cms_brand_name,
    concat('DATA START ', base64(cast(left(cms_generic_name, 1485) as blob)), ' DATA END') as cms_generic_name,
    case
        when biologic_proprietary_names is null then null
        else concat('DATA START ', base64(cast(left(biologic_proprietary_names, 1485) as blob)), ' DATA END')
    end as biologic_proprietary_names,
    concat('DATA START ', base64(cast(left(biologic_proper_name, 1485) as blob)), ' DATA END') as biologic_proper_name
from safe_matches;
