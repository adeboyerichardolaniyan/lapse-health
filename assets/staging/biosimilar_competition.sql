/* @bruin
name: staging.biosimilar_competition
type: duckdb.sql
materialization:
  type: table

depends:
  - staging.biologic_products
  - raw.purple_book

columns:
  - name: biologic_product_key
    type: varchar
    description: Reference biologic key from staging.biologic_products.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: biosimilar_product_count
    type: integer
    description: Count of approved 351(k) biosimilar or interchangeable product rows.
    checks:
      - name: not_null
  - name: biosimilar_bla_count
    type: integer
    description: Count of distinct approved 351(k) BLA numbers.
    checks:
      - name: not_null
  - name: interchangeable_product_count
    type: integer
    description: Count of approved interchangeable product rows.
    checks:
      - name: not_null
  - name: active_biosimilar_product_count
    type: integer
    description: Count of approved non-withdrawn 351(k) product rows.
    checks:
      - name: not_null
  - name: first_biosimilar_approval_date
    type: date
    description: Earliest parsed 351(k) approval date in the reference product group.
  - name: latest_biosimilar_approval_date
    type: date
    description: Latest parsed 351(k) approval date in the reference product group.
  - name: biosimilar_proprietary_names
    type: varchar
    description: Base64 encoded DATA START/END bounded, sanitized proprietary names for matched biosimilars/interchangeables.
  - name: biosimilar_applicants
    type: varchar
    description: Base64 encoded DATA START/END bounded, sanitized applicants for matched biosimilars/interchangeables.
  - name: competition_density_bucket
    type: varchar
    description: Competition-density category derived from approved biosimilar product count.
    checks:
      - name: not_null
  - name: competition_density_score
    type: decimal
    description: 0-100 attractiveness score where lower biosimilar competition receives a higher score.
    checks:
      - name: not_null

custom_checks:
  - name: every biologic product has competition row
    query: select abs((select count(*) from staging.biologic_products) - (select count(*) from staging.biosimilar_competition))
    value: 0
  - name: biosimilar competition keys are unique
    query: select count(*) from (select biologic_product_key from staging.biosimilar_competition group by 1 having count(*) > 1)
    value: 0
  - name: biosimilar counts are nonnegative
    query: select count(*) from staging.biosimilar_competition where biosimilar_product_count < 0 or biosimilar_bla_count < 0 or interchangeable_product_count < 0 or active_biosimilar_product_count < 0
    value: 0
  - name: biosimilar competition counts approved rows only
    query: select abs((select coalesce(sum(biosimilar_product_count), 0) from staging.biosimilar_competition) - (select count(distinct purple_book_product_key) from raw.purple_book where is_biosimilar = 'Yes' and cast(try_strptime(nullif(trim(approval_date), ''), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) as date) is not null))
    value: 0
  - name: biosimilar competition score is 0 to 100
    query: select count(*) from staging.biosimilar_competition where competition_density_score < 0 or competition_density_score > 100 or competition_density_score is null
    value: 0
  - name: biosimilar competition buckets use accepted values
    query: select count(*) from staging.biosimilar_competition where competition_density_bucket not in ('none', 'low', 'moderate', 'high', 'saturated')
    value: 0
  - name: higher biosimilar competition lowers density score
    query: select count(*) from staging.biosimilar_competition where biosimilar_product_count >= 6 and competition_density_score > 20
    value: 0
  - name: AI-facing biosimilar text is data bounded
    query: select count(*) from staging.biosimilar_competition where (biosimilar_proprietary_names is not null and (not regexp_matches(biosimilar_proprietary_names, '^DATA START [A-Za-z0-9+/=]+ DATA END$') or length(biosimilar_proprietary_names) > 2000)) or (biosimilar_applicants is not null and (not regexp_matches(biosimilar_applicants, '^DATA START [A-Za-z0-9+/=]+ DATA END$') or length(biosimilar_applicants) > 2000))
    value: 0
@bruin */

with raw_biosimilar_rows as (
    select
        reference_product_group_key as biologic_product_key,
        purple_book_product_key,
        nullif(trim(bla_number), '') as bla_number,
        case
            when nullif(trim(proprietary_name), '') is null
                or upper(nullif(trim(proprietary_name), '')) in ('N/A', 'NA', 'NOT APPLICABLE') then null
            else coalesce(
                nullif(
                    left(trim(regexp_replace(regexp_replace(proprietary_name, '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                    ''
                ),
                'unsupported text'
            )
        end as proprietary_name,
        case
            when nullif(trim(applicant), '') is null then null
            else coalesce(
                nullif(
                    left(trim(regexp_replace(regexp_replace(applicant, '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                    ''
                ),
                'unsupported text'
            )
        end as applicant,
        is_interchangeable,
        withdrawn_flag,
        cast(try_strptime(nullif(trim(approval_date), ''), ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) as date) as approval_date
    from raw.purple_book
    where is_biosimilar = 'Yes'
),
biosimilar_rows as (
    select *
    from raw_biosimilar_rows
    where approval_date is not null
),
rolled_up as (
    select
        biologic_product_key,
        count(distinct purple_book_product_key) as biosimilar_product_count,
        count(distinct bla_number) filter (where bla_number is not null) as biosimilar_bla_count,
        count(distinct purple_book_product_key) filter (where is_interchangeable = 'Yes') as interchangeable_product_count,
        count(distinct purple_book_product_key) filter (where withdrawn_flag = 'No') as active_biosimilar_product_count,
        min(approval_date) as first_biosimilar_approval_date,
        max(approval_date) as latest_biosimilar_approval_date,
        left(
            string_agg(distinct proprietary_name, ', ' order by proprietary_name)
                filter (where proprietary_name is not null),
            2000
        ) as biosimilar_proprietary_names,
        left(
            string_agg(distinct applicant, ', ' order by applicant)
                filter (where applicant is not null),
            2000
        ) as biosimilar_applicants
    from biosimilar_rows
    group by biologic_product_key
)
select
    biologic_products.biologic_product_key,
    coalesce(rolled_up.biosimilar_product_count, 0) as biosimilar_product_count,
    coalesce(rolled_up.biosimilar_bla_count, 0) as biosimilar_bla_count,
    coalesce(rolled_up.interchangeable_product_count, 0) as interchangeable_product_count,
    coalesce(rolled_up.active_biosimilar_product_count, 0) as active_biosimilar_product_count,
    rolled_up.first_biosimilar_approval_date,
    rolled_up.latest_biosimilar_approval_date,
    case
        when rolled_up.biosimilar_proprietary_names is null then null
        else concat('DATA START ', base64(cast(left(rolled_up.biosimilar_proprietary_names, 1485) as blob)), ' DATA END')
    end as biosimilar_proprietary_names,
    case
        when rolled_up.biosimilar_applicants is null then null
        else concat('DATA START ', base64(cast(left(rolled_up.biosimilar_applicants, 1485) as blob)), ' DATA END')
    end as biosimilar_applicants,
    case
        when coalesce(rolled_up.biosimilar_product_count, 0) = 0 then 'none'
        when coalesce(rolled_up.biosimilar_product_count, 0) <= 2 then 'low'
        when coalesce(rolled_up.biosimilar_product_count, 0) <= 5 then 'moderate'
        when coalesce(rolled_up.biosimilar_product_count, 0) <= 10 then 'high'
        else 'saturated'
    end as competition_density_bucket,
    cast(case
        when coalesce(rolled_up.biosimilar_product_count, 0) = 0 then 100
        when coalesce(rolled_up.biosimilar_product_count, 0) <= 2 then 80
        when coalesce(rolled_up.biosimilar_product_count, 0) <= 5 then 50
        when coalesce(rolled_up.biosimilar_product_count, 0) <= 10 then 20
        else 5
    end as decimal(5, 2)) as competition_density_score
from staging.biologic_products as biologic_products
left join rolled_up
    on biologic_products.biologic_product_key = rolled_up.biologic_product_key;
