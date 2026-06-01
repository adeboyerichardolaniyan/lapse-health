/* @bruin
name: staging.biologic_products
type: duckdb.sql
materialization:
  type: table

depends:
  - raw.purple_book

columns:
  - name: biologic_product_key
    type: varchar
    description: Stable reference biologic key from the Purple Book reference-product grouping.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: reference_product_group_key
    type: varchar
    description: Purple Book grouping key shared by a reference biologic and its biosimilars.
    checks:
      - name: not_null
  - name: proper_name
    type: varchar
    description: Comma-delimited sanitized reference biologic proper names, capped for AI analyst context.
    checks:
      - name: not_null
  - name: proper_name_key
    type: varchar
    description: Lowercase alphanumeric join key for the representative proper name selected by frequency, active-row frequency, length, then lexical order.
    checks:
      - name: not_null
  - name: proprietary_names
    type: varchar
    description: Comma-delimited sanitized Purple Book proprietary names for the reference biologic, capped for AI analyst context.
  - name: proprietary_name_key
    type: varchar
    description: Lowercase alphanumeric join key for the primary reference biologic proprietary name.
  - name: applicants
    type: varchar
    description: Comma-delimited sanitized reference biologic applicants, capped for AI analyst context.
  - name: reference_bla_numbers
    type: varchar
    description: Comma-delimited BLA numbers represented by this reference biologic group.
    checks:
      - name: not_null
  - name: reference_product_numbers
    type: varchar
    description: Comma-delimited Purple Book product numbers represented by this reference biologic group.
    checks:
      - name: not_null
  - name: reference_product_count
    type: integer
    description: Number of Purple Book 351(a) rows in this reference biologic group.
    checks:
      - name: not_null
  - name: active_reference_product_count
    type: integer
    description: Number of non-withdrawn reference product rows in this group.
    checks:
      - name: not_null
  - name: latest_exclusivity_expiration_date
    type: date
    description: Latest parsed reference-product or orphan exclusivity expiration date in this group.
  - name: latest_exclusivity_source
    type: varchar
    description: Source field that supplied the latest parsed exclusivity date.
  - name: marketing_statuses
    type: varchar
    description: Comma-delimited sanitized marketing statuses represented by this group.
  - name: licensure_statuses
    type: varchar
    description: Comma-delimited sanitized licensure statuses represented by this group.

custom_checks:
  - name: biologic product keys are unique
    query: select count(*) from (select biologic_product_key from staging.biologic_products group by 1 having count(*) > 1)
    value: 0
  - name: every reference biologic group is staged
    query: select abs((select count(distinct reference_product_group_key) from raw.purple_book where is_reference_product = 'Yes') - (select count(*) from staging.biologic_products))
    value: 0
  - name: reference product counts are positive
    query: select count(*) from staging.biologic_products where reference_product_count <= 0
    value: 0
  - name: biologic name keys are populated
    query: select count(*) from staging.biologic_products where proper_name_key is null or proper_name_key = ''
    value: 0
  - name: representative biologic proper name is emitted
    query: select count(*) from staging.biologic_products where left(nullif(trim(lower(regexp_replace(regexp_replace(coalesce(proper_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))), ''), length(proper_name_key)) <> proper_name_key
    value: 0
  - name: exclusivity source is populated when date is present
    query: select count(*) from staging.biologic_products where latest_exclusivity_expiration_date is not null and latest_exclusivity_source is null
    value: 0
  - name: AI-facing biologic text is constrained
    query: select count(*) from staging.biologic_products where regexp_matches(coalesce(proper_name, '') || coalesce(proprietary_names, '') || coalesce(applicants, '') || coalesce(marketing_statuses, '') || coalesce(licensure_statuses, ''), '[^A-Za-z0-9, ]') or length(coalesce(proper_name, '')) > 500 or length(coalesce(proprietary_names, '')) > 2000 or length(coalesce(applicants, '')) > 2000 or length(coalesce(marketing_statuses, '')) > 500 or length(coalesce(licensure_statuses, '')) > 500
    value: 0
@bruin */

with reference_rows as (
    select
        reference_product_group_key,
        coalesce(
            nullif(
                left(trim(regexp_replace(regexp_replace(coalesce(proper_name, ''), '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 500),
                ''
            ),
            'unsupported text'
        ) as proper_name,
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
        nullif(trim(bla_number), '') as bla_number,
        nullif(trim(product_number), '') as product_number,
        case
            when nullif(trim(marketing_status), '') is null then null
            else coalesce(
                nullif(
                    left(trim(regexp_replace(regexp_replace(marketing_status, '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 200),
                    ''
                ),
                'unknown'
            )
        end as marketing_status,
        case
            when nullif(trim(licensure), '') is null then null
            else coalesce(
                nullif(
                    left(trim(regexp_replace(regexp_replace(licensure, '[^A-Za-z0-9, ]+', ' ', 'g'), '[[:space:]]+', ' ', 'g')), 200),
                    ''
                ),
                'unknown'
            )
        end as licensure,
        withdrawn_flag,
        nullif(trim(exclusivity_expiration_date), '') as exclusivity_expiration_date,
        nullif(trim(reference_product_exclusivity_expiration_date), '') as reference_product_exclusivity_expiration_date,
        nullif(trim(orphan_exclusivity_expiration_date), '') as orphan_exclusivity_expiration_date
    from raw.purple_book
    where is_reference_product = 'Yes'
        and reference_product_group_key is not null
),
date_candidates as (
    select reference_product_group_key, 'exclusivity_expiration_date' as date_source, exclusivity_expiration_date as date_text
    from reference_rows
    union all
    select reference_product_group_key, 'reference_product_exclusivity_expiration_date' as date_source, reference_product_exclusivity_expiration_date as date_text
    from reference_rows
    union all
    select reference_product_group_key, 'orphan_exclusivity_expiration_date' as date_source, orphan_exclusivity_expiration_date as date_text
    from reference_rows
),
parsed_dates as (
    select
        reference_product_group_key,
        date_source,
        cast(try_strptime(date_text, ['%d-%b-%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%b %d, %Y', '%B %d, %Y']) as date) as parsed_date
    from date_candidates
    where date_text is not null
        and lower(trim(date_text)) not in ('date tbd', 'tbd', 'n/a', 'na', 'not applicable', 'not available', 'pending', 'unknown')
),
latest_dates as (
    select
        reference_product_group_key,
        parsed_date as latest_exclusivity_expiration_date,
        date_source as latest_exclusivity_source
    from (
        select
            reference_product_group_key,
            date_source,
            parsed_date,
            row_number() over (
                partition by reference_product_group_key
                order by parsed_date desc, date_source
            ) as date_rank
        from parsed_dates
        where parsed_date is not null
    )
    where date_rank = 1
),
proper_name_candidates as (
    select
        reference_product_group_key,
        proper_name,
        count(*) as proper_name_row_count,
        count(*) filter (where withdrawn_flag = 'No') as active_proper_name_row_count
    from reference_rows
    group by
        reference_product_group_key,
        proper_name
),
primary_proper_names as (
    select
        reference_product_group_key,
        proper_name as primary_proper_name
    from (
        select
            reference_product_group_key,
            proper_name,
            row_number() over (
                partition by reference_product_group_key
                order by
                    proper_name_row_count desc,
                    active_proper_name_row_count desc,
                    length(proper_name) desc,
                    proper_name
            ) as proper_name_rank
        from proper_name_candidates
    )
    where proper_name_rank = 1
),
proper_name_lists as (
    select
        proper_name_candidates.reference_product_group_key,
        string_agg(
            proper_name_candidates.proper_name,
            ', '
            order by
                case
                    when proper_name_candidates.proper_name = primary_proper_names.primary_proper_name then 0
                    else 1
                end,
                proper_name_candidates.proper_name
        ) as proper_name
    from proper_name_candidates
    inner join primary_proper_names
        on proper_name_candidates.reference_product_group_key = primary_proper_names.reference_product_group_key
    group by proper_name_candidates.reference_product_group_key
),
rolled_up as (
    select
        reference_product_group_key as biologic_product_key,
        reference_product_group_key,
        min(proprietary_name) filter (where proprietary_name is not null) as primary_proprietary_name,
        string_agg(distinct proprietary_name, ', ' order by proprietary_name) filter (where proprietary_name is not null) as proprietary_names,
        string_agg(distinct applicant, ', ' order by applicant) filter (where applicant is not null) as applicants,
        string_agg(distinct bla_number, ', ' order by bla_number) as reference_bla_numbers,
        string_agg(distinct product_number, ', ' order by product_number) as reference_product_numbers,
        count(*) as reference_product_count,
        count(*) filter (where withdrawn_flag = 'No') as active_reference_product_count,
        string_agg(distinct marketing_status, ', ' order by marketing_status) filter (where marketing_status is not null) as marketing_statuses,
        string_agg(distinct licensure, ', ' order by licensure) filter (where licensure is not null) as licensure_statuses
    from reference_rows
    group by reference_product_group_key
)
select
    rolled_up.biologic_product_key,
    rolled_up.reference_product_group_key,
    left(proper_name_lists.proper_name, 500) as proper_name,
    nullif(
        trim(lower(regexp_replace(regexp_replace(coalesce(primary_proper_names.primary_proper_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))),
        ''
    ) as proper_name_key,
    left(rolled_up.proprietary_names, 2000) as proprietary_names,
    nullif(
        trim(lower(regexp_replace(regexp_replace(coalesce(rolled_up.primary_proprietary_name, ''), '[^A-Za-z0-9]+', ' ', 'g'), '[[:space:]]+', ' ', 'g'))),
        ''
    ) as proprietary_name_key,
    left(rolled_up.applicants, 2000) as applicants,
    rolled_up.reference_bla_numbers,
    rolled_up.reference_product_numbers,
    rolled_up.reference_product_count,
    rolled_up.active_reference_product_count,
    latest_dates.latest_exclusivity_expiration_date,
    latest_dates.latest_exclusivity_source,
    left(rolled_up.marketing_statuses, 500) as marketing_statuses,
    left(rolled_up.licensure_statuses, 500) as licensure_statuses
from rolled_up
inner join primary_proper_names
    on rolled_up.reference_product_group_key = primary_proper_names.reference_product_group_key
inner join proper_name_lists
    on rolled_up.reference_product_group_key = proper_name_lists.reference_product_group_key
left join latest_dates
    on rolled_up.reference_product_group_key = latest_dates.reference_product_group_key;
