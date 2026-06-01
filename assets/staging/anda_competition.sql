/* @bruin
name: staging.anda_competition
type: duckdb.sql
materialization:
  type: table

depends:
  - staging.branded_drugs
  - raw.openfda_anda_products

columns:
  - name: appl_no
    type: varchar
    description: FDA NDA application number. One row per branded application.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: match_method
    type: varchar
    description: ANDA match method used for this branded application.
    checks:
      - name: not_null
  - name: matched_anda_application_count
    type: integer
    description: Count of distinct openFDA ANDA applications matched on ingredient and dosage route.
    checks:
      - name: not_null
  - name: matched_anda_product_count
    type: integer
    description: Count of distinct openFDA ANDA products matched on ingredient and dosage route.
    checks:
      - name: not_null
  - name: matched_anda_sponsor_count
    type: integer
    description: Count of distinct ANDA sponsors among matched applications.
    checks:
      - name: not_null
  - name: ab_rated_anda_application_count
    type: integer
    description: Count of distinct matched ANDA applications with at least one AB-family TE code.
    checks:
      - name: not_null
  - name: prescription_anda_application_count
    type: integer
    description: Count of distinct matched ANDA applications with prescription marketing status.
    checks:
      - name: not_null
  - name: earliest_anda_approval_date
    type: date
    description: Earliest original approval date among matched ANDA applications.
  - name: latest_anda_approval_date
    type: date
    description: Latest original approval date among matched ANDA applications.
  - name: matched_anda_application_numbers
    type: varchar
    description: Comma-delimited matched ANDA application numbers.
  - name: matched_anda_sponsors
    type: varchar
    description: Comma-delimited sanitized matched ANDA sponsor names, capped for AI analyst context.
  - name: matched_anda_brand_names
    type: varchar
    description: Comma-delimited sanitized matched openFDA product brand names, capped for AI analyst context.
  - name: matched_anda_te_codes
    type: varchar
    description: Comma-delimited sanitized matched therapeutic equivalence codes.
  - name: competition_density_bucket
    type: varchar
    description: Competition-density category derived from matched ANDA application count.
    checks:
      - name: not_null
  - name: competition_density_score
    type: decimal
    description: 0-100 attractiveness score where lower generic competition receives a higher score.
    checks:
      - name: not_null

custom_checks:
  - name: every branded application has a competition row
    query: select abs((select count(distinct appl_no) from staging.branded_drugs) - (select count(*) from staging.anda_competition))
    value: 0
  - name: competition applications are unique
    query: select count(*) from (select appl_no from staging.anda_competition group by 1 having count(*) > 1)
    value: 0
  - name: competition counts are nonnegative
    query: select count(*) from staging.anda_competition where matched_anda_application_count < 0 or matched_anda_product_count < 0 or matched_anda_sponsor_count < 0 or ab_rated_anda_application_count < 0 or prescription_anda_application_count < 0
    value: 0
  - name: competition score is 0 to 100
    query: select count(*) from staging.anda_competition where competition_density_score < 0 or competition_density_score > 100 or competition_density_score is null
    value: 0
  - name: competition buckets use accepted values
    query: select count(*) from staging.anda_competition where competition_density_bucket not in ('none', 'low', 'moderate', 'high', 'saturated')
    value: 0
  - name: match method uses accepted values
    query: select count(*) from staging.anda_competition where match_method not in ('ingredient_and_route', 'none')
    value: 0
  - name: high generic competition lowers density score
    query: select count(*) from staging.anda_competition where matched_anda_application_count >= 16 and competition_density_score > 10
    value: 0
  - name: AI-facing ANDA text is constrained
    query: select count(*) from staging.anda_competition where regexp_matches(coalesce(matched_anda_application_numbers, '') || coalesce(matched_anda_sponsors, '') || coalesce(matched_anda_brand_names, '') || coalesce(matched_anda_te_codes, ''), '[^A-Za-z0-9, ]') or length(coalesce(matched_anda_application_numbers, '')) > 2000 or length(coalesce(matched_anda_sponsors, '')) > 2000 or length(coalesce(matched_anda_brand_names, '')) > 2000 or length(coalesce(matched_anda_te_codes, '')) > 500
    value: 0
@bruin */

with branded_applications as (
    select distinct appl_no
    from staging.branded_drugs
),
branded_product_base as (
    select distinct
        appl_no,
        branded_product_key,
        ingredient,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(coalesce(dosage_form_route, ''), '[^A-Za-z0-9]+', ' ', 'g'),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as dosage_route_key
    from staging.branded_drugs
    where ingredient is not null
),
branded_ingredient_parts as (
    select
        branded_product_base.appl_no,
        branded_product_base.branded_product_key,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(coalesce(ingredient_parts.ingredient_part, ''), '[^A-Za-z0-9]+', ' ', 'g'),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as ingredient_part_key
    from branded_product_base
    cross join unnest(string_split(coalesce(branded_product_base.ingredient, ''), ';')) as ingredient_parts(ingredient_part)
),
branded_products as (
    select
        branded_product_base.appl_no,
        branded_product_base.branded_product_key,
        string_agg(
            distinct branded_ingredient_parts.ingredient_part_key,
            ' '
            order by branded_ingredient_parts.ingredient_part_key
        ) as ingredient_key,
        branded_product_base.dosage_route_key
    from branded_product_base
    inner join branded_ingredient_parts
        on branded_product_base.appl_no = branded_ingredient_parts.appl_no
        and branded_product_base.branded_product_key = branded_ingredient_parts.branded_product_key
    where branded_ingredient_parts.ingredient_part_key is not null
    group by
        branded_product_base.appl_no,
        branded_product_base.branded_product_key,
        branded_product_base.dosage_route_key
),
anda_product_base as (
    select
        anda_product_key,
        application_number,
        anda_appl_no,
        nullif(trim(sponsor_name), '') as sponsor_name,
        nullif(trim(brand_name), '') as brand_name,
        active_ingredient_names,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(
                            concat(coalesce(dosage_form, ''), ' ', coalesce(route, '')),
                            '[^A-Za-z0-9]+',
                            ' ',
                            'g'
                        ),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as dosage_route_key,
        nullif(trim(marketing_status), '') as marketing_status,
        nullif(trim(te_code), '') as te_code,
        coalesce(te_code, '') like 'AB%' as is_ab_rated,
        cast(try_strptime(nullif(trim(original_approval_date), ''), '%Y%m%d') as date) as original_approval_date
    from raw.openfda_anda_products
    where application_number like 'ANDA%'
),
anda_ingredient_parts as (
    select
        anda_product_base.anda_product_key,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(coalesce(ingredient_parts.ingredient_part, ''), '[^A-Za-z0-9]+', ' ', 'g'),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as ingredient_part_key
    from anda_product_base
    cross join unnest(string_split(coalesce(anda_product_base.active_ingredient_names, ''), ',')) as ingredient_parts(ingredient_part)
),
anda_ingredient_keys as (
    select
        anda_product_key,
        string_agg(
            distinct ingredient_part_key,
            ' '
            order by ingredient_part_key
        ) as active_ingredient_key
    from anda_ingredient_parts
    where ingredient_part_key is not null
    group by anda_product_key
),
anda_products as (
    select
        anda_product_base.anda_product_key,
        anda_product_base.application_number,
        anda_product_base.anda_appl_no,
        anda_product_base.sponsor_name,
        anda_product_base.brand_name,
        anda_ingredient_keys.active_ingredient_key,
        anda_product_base.dosage_route_key,
        anda_product_base.marketing_status,
        anda_product_base.te_code,
        anda_product_base.is_ab_rated,
        anda_product_base.original_approval_date
    from anda_product_base
    inner join anda_ingredient_keys
        on anda_product_base.anda_product_key = anda_ingredient_keys.anda_product_key
),
matched_products as (
    select distinct
        branded_products.appl_no,
        anda_products.anda_product_key,
        anda_products.application_number,
        anda_products.sponsor_name,
        anda_products.brand_name,
        anda_products.marketing_status,
        anda_products.te_code,
        anda_products.is_ab_rated,
        anda_products.original_approval_date
    from branded_products
    inner join anda_products
        on branded_products.ingredient_key = anda_products.active_ingredient_key
        and branded_products.dosage_route_key = anda_products.dosage_route_key
    where branded_products.dosage_route_key is not null
        and anda_products.dosage_route_key is not null
),
application_flags as (
    select
        appl_no,
        application_number,
        max(case when is_ab_rated then 1 else 0 end) as has_ab_rated_product,
        max(case when lower(marketing_status) = 'prescription' then 1 else 0 end) as has_prescription_product
    from matched_products
    group by
        appl_no,
        application_number
),
application_rollup as (
    select
        appl_no,
        coalesce(sum(has_ab_rated_product), 0) as ab_rated_anda_application_count,
        coalesce(sum(has_prescription_product), 0) as prescription_anda_application_count
    from application_flags
    group by appl_no
),
product_rollup as (
    select
        matched_products.appl_no,
        count(distinct matched_products.application_number) as matched_anda_application_count,
        count(distinct matched_products.anda_product_key) as matched_anda_product_count,
        count(distinct matched_products.sponsor_name) filter (where matched_products.sponsor_name is not null) as matched_anda_sponsor_count,
        min(matched_products.original_approval_date) as earliest_anda_approval_date,
        max(matched_products.original_approval_date) as latest_anda_approval_date,
        string_agg(distinct matched_products.application_number, ', ' order by matched_products.application_number) as matched_anda_application_numbers,
        left(
            string_agg(distinct matched_products.sponsor_name, ', ' order by matched_products.sponsor_name)
                filter (where matched_products.sponsor_name is not null),
            2000
        ) as matched_anda_sponsors,
        left(
            string_agg(distinct matched_products.brand_name, ', ' order by matched_products.brand_name)
                filter (where matched_products.brand_name is not null),
            2000
        ) as matched_anda_brand_names,
        string_agg(distinct matched_products.te_code, ', ' order by matched_products.te_code)
            filter (where matched_products.te_code is not null) as matched_anda_te_codes
    from matched_products
    group by matched_products.appl_no
),
competition_rollup as (
    select
        product_rollup.appl_no,
        product_rollup.matched_anda_application_count,
        product_rollup.matched_anda_product_count,
        product_rollup.matched_anda_sponsor_count,
        coalesce(application_rollup.ab_rated_anda_application_count, 0) as ab_rated_anda_application_count,
        coalesce(application_rollup.prescription_anda_application_count, 0) as prescription_anda_application_count,
        product_rollup.earliest_anda_approval_date,
        product_rollup.latest_anda_approval_date,
        product_rollup.matched_anda_application_numbers,
        product_rollup.matched_anda_sponsors,
        product_rollup.matched_anda_brand_names,
        product_rollup.matched_anda_te_codes
    from product_rollup
    left join application_rollup
        on product_rollup.appl_no = application_rollup.appl_no
),
scored as (
    select
        branded_applications.appl_no,
        case
            when competition_rollup.appl_no is null then 'none'
            else 'ingredient_and_route'
        end as match_method,
        coalesce(competition_rollup.matched_anda_application_count, 0) as matched_anda_application_count,
        coalesce(competition_rollup.matched_anda_product_count, 0) as matched_anda_product_count,
        coalesce(competition_rollup.matched_anda_sponsor_count, 0) as matched_anda_sponsor_count,
        coalesce(competition_rollup.ab_rated_anda_application_count, 0) as ab_rated_anda_application_count,
        coalesce(competition_rollup.prescription_anda_application_count, 0) as prescription_anda_application_count,
        competition_rollup.earliest_anda_approval_date,
        competition_rollup.latest_anda_approval_date,
        competition_rollup.matched_anda_application_numbers,
        competition_rollup.matched_anda_sponsors,
        competition_rollup.matched_anda_brand_names,
        competition_rollup.matched_anda_te_codes
    from branded_applications
    left join competition_rollup
        on branded_applications.appl_no = competition_rollup.appl_no
)
select
    *,
    case
        when matched_anda_application_count = 0 then 'none'
        when matched_anda_application_count = 1 then 'low'
        when matched_anda_application_count between 2 and 3 then 'moderate'
        when matched_anda_application_count between 4 and 15 then 'high'
        else 'saturated'
    end as competition_density_bucket,
    case
        when matched_anda_application_count = 0 then 100.0
        when matched_anda_application_count = 1 then 85.0
        when matched_anda_application_count between 2 and 3 then 65.0
        when matched_anda_application_count between 4 and 7 then 45.0
        when matched_anda_application_count between 8 and 15 then 25.0
        else 10.0
    end as competition_density_score
from scored;
