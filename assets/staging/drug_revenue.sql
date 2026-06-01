/* @bruin
name: staging.drug_revenue
type: duckdb.sql
materialization:
  type: table

depends:
  - raw.cms_part_d
  - raw.cms_part_b

columns:
  - name: cms_drug_key
    type: varchar
    description: Stable CMS drug key built from normalized brand and generic names.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: source_program
    type: varchar
    description: Medicare source coverage represented by this normalized drug row.
    checks:
      - name: not_null
  - name: brand_name
    type: varchar
    description: Sanitized CMS brand names from source aggregate rows, capped for AI analyst context.
    checks:
      - name: not_null
  - name: brand_name_key
    type: varchar
    description: Lowercase alphanumeric join key for the CMS brand name.
    checks:
      - name: not_null
  - name: generic_name
    type: varchar
    description: Sanitized CMS generic names from source aggregate rows, capped for AI analyst context.
    checks:
      - name: not_null
  - name: generic_name_key
    type: varchar
    description: Lowercase alphanumeric join key for the CMS generic name.
    checks:
      - name: not_null
  - name: total_manufacturers
    type: integer
    description: CMS Part D total manufacturer count when Part D contributes to this row.
  - name: total_manufacturer_value_count
    type: integer
    description: Count of distinct raw Part D total_manufacturers values within this normalized CMS drug key.
  - name: raw_cms_row_count
    type: integer
    description: Number of raw CMS aggregate rows represented by this normalized drug key.
  - name: part_d_raw_cms_row_count
    type: integer
    description: Number of raw CMS Part D rows represented by this normalized drug key.
  - name: part_b_raw_cms_row_count
    type: integer
    description: Number of raw CMS Part B rows represented by this normalized drug key.
  - name: source_year
    type: integer
    description: Latest annual source year represented by the CMS files.
    checks:
      - name: not_null
  - name: total_spending_2019
    type: decimal
    description: 2019 total Medicare spending across represented source programs.
  - name: total_spending_2020
    type: decimal
    description: 2020 total Medicare spending across represented source programs.
  - name: total_spending_2021
    type: decimal
    description: 2021 total Medicare spending across represented source programs.
  - name: total_spending_2022
    type: decimal
    description: 2022 total Medicare spending across represented source programs.
  - name: total_spending_2023
    type: decimal
    description: 2023 total Medicare spending across represented source programs.
    checks:
      - name: not_null
  - name: part_d_total_spending_2023
    type: decimal
    description: 2023 CMS Part D spending contributing to this normalized drug row.
  - name: part_b_total_spending_2023
    type: decimal
    description: 2023 CMS Part B spending contributing to this normalized drug row.
  - name: total_claims_2023
    type: bigint
    description: 2023 total Medicare claims across represented source programs.
  - name: total_beneficiaries_2023
    type: bigint
    description: 2023 total Medicare beneficiaries for single-source rows; null when Part B has multiple HCPCS rows or both programs contribute because beneficiary counts are non-exclusive.
  - name: avg_spending_per_claim_2023
    type: decimal
    description: 2023 average spending per claim recalculated from the combined totals.
  - name: avg_spending_per_beneficiary_2023
    type: decimal
    description: 2023 average spending per beneficiary for single-source rows; null when Part B has multiple HCPCS rows or both programs contribute because beneficiary counts may overlap.
  - name: cagr_avg_spending_per_dosage_unit_2019_2023
    type: decimal
    description: CMS-reported CAGR in average spending per dosage unit when exactly one source row contributes.
  - name: outlier_flag_2023
    type: varchar
    description: Yes when any represented CMS source row is marked as a 2023 outlier.
    checks:
      - name: not_null

custom_checks:
  - name: eligible CMS source rows are staged once
    query: |
      with source_rows as (
          select
              nullif(trim(lower(regexp_replace(regexp_replace(coalesce(brand_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))), '') as brand_name_key,
              nullif(trim(lower(regexp_replace(regexp_replace(coalesce(generic_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))), '') as generic_name_key
          from raw.cms_part_d
          where trim(manufacturer_name) = 'Overall'
          union all
          select
              nullif(trim(lower(regexp_replace(regexp_replace(coalesce(brand_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))), '') as brand_name_key,
              nullif(trim(lower(regexp_replace(regexp_replace(coalesce(generic_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))), '') as generic_name_key
          from raw.cms_part_b
      )
      select abs(
          (select coalesce(sum(raw_cms_row_count), 0) from staging.drug_revenue)
          - (select count(*) from source_rows where brand_name_key is not null and generic_name_key is not null)
      )
    value: 0
  - name: CMS source year is accepted
    query: select count(*) from staging.drug_revenue where source_year <> 2023
    value: 0
  - name: CMS 2023 spending is nonnegative
    query: select count(*) from staging.drug_revenue where total_spending_2023 < 0 or part_d_total_spending_2023 < 0 or part_b_total_spending_2023 < 0
    value: 0
  - name: CMS aggregate keys are unique
    query: select count(*) from (select cms_drug_key from staging.drug_revenue group by 1 having count(*) > 1)
    value: 0
  - name: source program labels are accepted
    query: select count(*) from staging.drug_revenue where source_program not in ('part_b', 'part_d', 'part_b_and_part_d')
    value: 0
  - name: source program row counts are consistent
    query: select count(*) from staging.drug_revenue where raw_cms_row_count <> part_d_raw_cms_row_count + part_b_raw_cms_row_count or (source_program = 'part_d' and (part_d_raw_cms_row_count <= 0 or part_b_raw_cms_row_count <> 0)) or (source_program = 'part_b' and (part_b_raw_cms_row_count <= 0 or part_d_raw_cms_row_count <> 0)) or (source_program = 'part_b_and_part_d' and (part_b_raw_cms_row_count <= 0 or part_d_raw_cms_row_count <= 0))
    value: 0
  - name: Part B spending is preserved from Tot_Spndng
    query: |
      with part_b_source as (
          select
              sum(try_cast(nullif(trim(total_spending_2023), '') as decimal(18, 2))) as source_spending
          from raw.cms_part_b
          where nullif(trim(lower(regexp_replace(regexp_replace(coalesce(brand_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))), '') is not null
              and nullif(trim(lower(regexp_replace(regexp_replace(coalesce(generic_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))), '') is not null
      ),
      staged as (
          select sum(part_b_total_spending_2023) as staged_spending
          from staging.drug_revenue
      )
      select case
          when abs((select source_spending from part_b_source) - (select staged_spending from staged)) < 0.01 then 0
          else 1
      end
    value: 0
  - name: Part B source is HCPCS aggregate grain
    query: select count(*) from (select cms_part_b_hcpcs_key from raw.cms_part_b group by 1 having count(*) > 1)
    value: 0
  - name: duplicate CMS manufacturer counts are consistent for Part D rows
    query: select count(*) from staging.drug_revenue where part_d_raw_cms_row_count > 0 and total_manufacturer_value_count <> 1
    value: 0
  - name: AI-facing CMS text is constrained
    query: select count(*) from staging.drug_revenue where regexp_matches(coalesce(brand_name, '') || coalesce(generic_name, ''), '[^A-Za-z0-9, ]') or length(coalesce(brand_name, '')) > 2000 or length(coalesce(generic_name, '')) > 2000
    value: 0
  - name: nonexclusive beneficiary metrics are not emitted
    query: select count(*) from staging.drug_revenue where (source_program = 'part_b_and_part_d' or part_b_raw_cms_row_count > 1) and (total_beneficiaries_2023 is not null or avg_spending_per_beneficiary_2023 is not null)
    value: 0
  - name: CAGR only emits for single source rows
    query: select count(*) from staging.drug_revenue where raw_cms_row_count <> 1 and cagr_avg_spending_per_dosage_unit_2019_2023 is not null
    value: 0
  - name: outlier flag is binary
    query: select count(*) from staging.drug_revenue where outlier_flag_2023 not in ('0', '1')
    value: 0
@bruin */

with part_d_rows as (
    select
        'part_d' as source_program,
        nullif(trim(brand_name), '') as brand_name,
        nullif(trim(generic_name), '') as generic_name,
        try_cast(nullif(trim(total_manufacturers), '') as integer) as total_manufacturers,
        try_cast(nullif(trim(source_year), '') as integer) as source_year,
        try_cast(nullif(trim(total_spending_2019), '') as decimal(18, 2)) as total_spending_2019,
        try_cast(nullif(trim(total_spending_2020), '') as decimal(18, 2)) as total_spending_2020,
        try_cast(nullif(trim(total_spending_2021), '') as decimal(18, 2)) as total_spending_2021,
        try_cast(nullif(trim(total_spending_2022), '') as decimal(18, 2)) as total_spending_2022,
        try_cast(nullif(trim(total_spending_2023), '') as decimal(18, 2)) as total_spending_2023,
        try_cast(nullif(trim(total_claims_2023), '') as bigint) as total_claims_2023,
        try_cast(nullif(trim(total_beneficiaries_2023), '') as bigint) as total_beneficiaries_2023,
        try_cast(nullif(trim(cagr_avg_spending_per_dosage_unit_2019_2023), '') as decimal(18, 6)) as cagr_avg_spending_per_dosage_unit_2019_2023,
        nullif(trim(outlier_flag_2023), '') as outlier_flag_2023
    from raw.cms_part_d
    where trim(manufacturer_name) = 'Overall'
),
part_b_rows as (
    select
        'part_b' as source_program,
        nullif(trim(brand_name), '') as brand_name,
        nullif(trim(generic_name), '') as generic_name,
        cast(null as integer) as total_manufacturers,
        try_cast(nullif(trim(source_year), '') as integer) as source_year,
        try_cast(nullif(trim(total_spending_2019), '') as decimal(18, 2)) as total_spending_2019,
        try_cast(nullif(trim(total_spending_2020), '') as decimal(18, 2)) as total_spending_2020,
        try_cast(nullif(trim(total_spending_2021), '') as decimal(18, 2)) as total_spending_2021,
        try_cast(nullif(trim(total_spending_2022), '') as decimal(18, 2)) as total_spending_2022,
        try_cast(nullif(trim(total_spending_2023), '') as decimal(18, 2)) as total_spending_2023,
        try_cast(nullif(trim(total_claims_2023), '') as bigint) as total_claims_2023,
        try_cast(nullif(trim(total_beneficiaries_2023), '') as bigint) as total_beneficiaries_2023,
        try_cast(nullif(trim(cagr_avg_spending_per_dosage_unit_2019_2023), '') as decimal(18, 6)) as cagr_avg_spending_per_dosage_unit_2019_2023,
        nullif(trim(outlier_flag_2023), '') as outlier_flag_2023
    from raw.cms_part_b
),
source_rows as (
    select * from part_d_rows
    union all
    select * from part_b_rows
),
normalized as (
    select
        source_program,
        brand_name,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(coalesce(brand_name, ''), '[^A-Za-z0-9]+', ' ', 'g'),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as brand_name_key,
        generic_name,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(coalesce(generic_name, ''), '[^A-Za-z0-9]+', ' ', 'g'),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as generic_name_key,
        total_manufacturers,
        source_year,
        total_spending_2019,
        total_spending_2020,
        total_spending_2021,
        total_spending_2022,
        total_spending_2023,
        total_claims_2023,
        total_beneficiaries_2023,
        cagr_avg_spending_per_dosage_unit_2019_2023,
        outlier_flag_2023
    from source_rows
),
eligible_rows as (
    select
        *,
        coalesce(
            nullif(
                left(trim(regexp_replace(regexp_replace(coalesce(brand_name, ''), '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                ''
            ),
            'unsupported text'
        ) as safe_brand_name,
        coalesce(
            nullif(
                left(trim(regexp_replace(regexp_replace(coalesce(generic_name, ''), '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                ''
            ),
            'unsupported text'
        ) as safe_generic_name
    from normalized
    where brand_name_key is not null
        and generic_name_key is not null
)
select
    concat(brand_name_key, '|', generic_name_key) as cms_drug_key,
    case
        when count(*) filter (where source_program = 'part_b') > 0
            and count(*) filter (where source_program = 'part_d') > 0 then 'part_b_and_part_d'
        when count(*) filter (where source_program = 'part_b') > 0 then 'part_b'
        else 'part_d'
    end as source_program,
    left(string_agg(distinct safe_brand_name, ', ' order by safe_brand_name), 2000) as brand_name,
    brand_name_key,
    left(string_agg(distinct safe_generic_name, ', ' order by safe_generic_name), 2000) as generic_name,
    generic_name_key,
    case
        when count(distinct total_manufacturers) filter (where source_program = 'part_d') = 1 then min(total_manufacturers)
    end as total_manufacturers,
    count(distinct total_manufacturers) filter (where source_program = 'part_d') as total_manufacturer_value_count,
    count(*) as raw_cms_row_count,
    count(*) filter (where source_program = 'part_d') as part_d_raw_cms_row_count,
    count(*) filter (where source_program = 'part_b') as part_b_raw_cms_row_count,
    max(source_year) as source_year,
    sum(total_spending_2019) as total_spending_2019,
    sum(total_spending_2020) as total_spending_2020,
    sum(total_spending_2021) as total_spending_2021,
    sum(total_spending_2022) as total_spending_2022,
    sum(total_spending_2023) as total_spending_2023,
    coalesce(sum(total_spending_2023) filter (where source_program = 'part_d'), 0) as part_d_total_spending_2023,
    coalesce(sum(total_spending_2023) filter (where source_program = 'part_b'), 0) as part_b_total_spending_2023,
    sum(total_claims_2023) as total_claims_2023,
    case
        when count(*) filter (where source_program = 'part_b') > 1
            or (
                count(*) filter (where source_program = 'part_b') > 0
                and count(*) filter (where source_program = 'part_d') > 0
            ) then null
        else sum(total_beneficiaries_2023)
    end as total_beneficiaries_2023,
    cast(sum(total_spending_2023) / nullif(sum(total_claims_2023), 0) as decimal(18, 2)) as avg_spending_per_claim_2023,
    case
        when count(*) filter (where source_program = 'part_b') > 1
            or (
                count(*) filter (where source_program = 'part_b') > 0
                and count(*) filter (where source_program = 'part_d') > 0
            ) then null
        else cast(sum(total_spending_2023) / nullif(sum(total_beneficiaries_2023), 0) as decimal(18, 2))
    end as avg_spending_per_beneficiary_2023,
    case
        when count(*) = 1 then max(cagr_avg_spending_per_dosage_unit_2019_2023)
    end as cagr_avg_spending_per_dosage_unit_2019_2023,
    case
        when max(case when upper(coalesce(outlier_flag_2023, '')) in ('1', 'Y', 'YES', 'TRUE') then 1 else 0 end) = 1 then '1'
        when max(case when upper(coalesce(outlier_flag_2023, '')) in ('0', 'N', 'NO', 'FALSE') then 1 else 0 end) = 1 then '0'
        else '0'
    end as outlier_flag_2023
from eligible_rows
group by
    brand_name_key,
    generic_name_key;
