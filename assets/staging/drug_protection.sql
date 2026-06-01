/* @bruin
name: staging.drug_protection
type: duckdb.sql
materialization:
  type: table

depends:
  - staging.branded_drugs
  - raw.ob_patents
  - raw.ob_exclusivity

columns:
  - name: appl_no
    type: varchar
    description: FDA NDA application number.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: patent_row_count
    type: integer
    description: Number of raw patent rows for this NDA.
  - name: distinct_patent_count
    type: integer
    description: Distinct listed patents for this NDA.
  - name: drug_substance_patent_count
    type: integer
    description: Distinct patents flagged as drug substance patents.
  - name: drug_product_patent_count
    type: integer
    description: Distinct patents flagged as drug product patents.
  - name: delisted_patent_count
    type: integer
    description: Distinct patents with an Orange Book delist flag.
  - name: earliest_patent_expiration_date
    type: date
    description: Earliest parsed patent expiration date for this NDA.
  - name: latest_patent_expiration_date
    type: date
    description: Latest parsed patent expiration date for this NDA.
  - name: patent_expiration_date_texts
    type: varchar
    description: Distinct raw patent expiration date texts seen for this NDA.
  - name: unparseable_patent_expiration_date_texts
    type: varchar
    description: Raw patent expiration date texts that failed explicit parsing.
  - name: patent_unparseable_date_count
    type: integer
    description: Count of patent rows with nonblank but unparseable expiration dates.
  - name: exclusivity_row_count
    type: integer
    description: Number of raw exclusivity rows for this NDA.
  - name: distinct_exclusivity_code_count
    type: integer
    description: Count of distinct exclusivity codes for this NDA.
  - name: earliest_exclusivity_expiration_date
    type: date
    description: Earliest parsed exclusivity expiration date for this NDA.
  - name: latest_exclusivity_expiration_date
    type: date
    description: Latest parsed exclusivity expiration date for this NDA.
  - name: exclusivity_expiration_date_texts
    type: varchar
    description: Distinct raw exclusivity expiration date texts seen for this NDA.
  - name: unparseable_exclusivity_expiration_date_texts
    type: varchar
    description: Raw exclusivity expiration date texts that failed explicit parsing.
  - name: exclusivity_unparseable_date_count
    type: integer
    description: Count of exclusivity rows with nonblank but unparseable expiration dates.
  - name: last_protection_date
    type: date
    description: Latest parsed patent or exclusivity expiration date for this NDA.

custom_checks:
  - name: protection keys are unique
    query: select count(*) from (select appl_no from staging.drug_protection group by 1 having count(*) > 1)
    value: 0
  - name: patent dates parse cleanly
    query: select count(*) from staging.drug_protection where patent_unparseable_date_count > 0
    value: 0
  - name: exclusivity dates parse cleanly
    query: select count(*) from staging.drug_protection where exclusivity_unparseable_date_count > 0
    value: 0
  - name: patent flags use accepted values
    query: select count(*) from raw.ob_patents where coalesce(nullif(trim(drug_substance_flag), ''), 'blank') not in ('Y', 'blank') or coalesce(nullif(trim(drug_product_flag), ''), 'blank') not in ('Y', 'blank') or coalesce(nullif(trim(delist_flag), ''), 'blank') not in ('Y', 'blank')
    value: 0
@bruin */

with applications as (
    select distinct appl_no
    from staging.branded_drugs
),
patents as (
    select
        nullif(trim(appl_no), '') as appl_no,
        nullif(trim(patent_no), '') as patent_no,
        nullif(trim(patent_expire_date_text), '') as patent_expiration_date_text,
        cast(
            try_strptime(
                regexp_replace(
                    nullif(regexp_replace(trim(patent_expire_date_text), '[[:space:]]+', ' ', 'g'), ''),
                    '^([A-Za-z]+) ([0-9]), ([0-9]{4})$',
                    '\1 0\2, \3'
                ),
                ['%b %d, %Y', '%B %d, %Y']
            ) as date
        ) as patent_expiration_date,
        upper(nullif(trim(drug_substance_flag), '')) as drug_substance_flag,
        upper(nullif(trim(drug_product_flag), '')) as drug_product_flag,
        upper(nullif(trim(delist_flag), '')) as delist_flag
    from raw.ob_patents
    where upper(trim(appl_type)) = 'N'
),
patent_agg as (
    select
        appl_no,
        count(*) as patent_row_count,
        count(distinct patent_no) as distinct_patent_count,
        count(distinct case when drug_substance_flag = 'Y' then patent_no end) as drug_substance_patent_count,
        count(distinct case when drug_product_flag = 'Y' then patent_no end) as drug_product_patent_count,
        count(distinct case when delist_flag = 'Y' then patent_no end) as delisted_patent_count,
        min(patent_expiration_date) as earliest_patent_expiration_date,
        max(patent_expiration_date) as latest_patent_expiration_date,
        string_agg(distinct patent_expiration_date_text, '; ' order by patent_expiration_date_text)
            filter (where patent_expiration_date_text is not null) as patent_expiration_date_texts,
        string_agg(distinct patent_expiration_date_text, '; ' order by patent_expiration_date_text)
            filter (
                where patent_expiration_date_text is not null
                    and patent_expiration_date is null
            ) as unparseable_patent_expiration_date_texts,
        count(*) filter (
            where patent_expiration_date_text is not null
                and patent_expiration_date is null
        ) as patent_unparseable_date_count
    from patents
    group by appl_no
),
exclusivities as (
    select
        nullif(trim(appl_no), '') as appl_no,
        nullif(trim(exclusivity_code), '') as exclusivity_code,
        nullif(trim(exclusivity_date), '') as exclusivity_expiration_date_text,
        cast(
            try_strptime(
                regexp_replace(
                    nullif(regexp_replace(trim(exclusivity_date), '[[:space:]]+', ' ', 'g'), ''),
                    '^([A-Za-z]+) ([0-9]), ([0-9]{4})$',
                    '\1 0\2, \3'
                ),
                ['%b %d, %Y', '%B %d, %Y']
            ) as date
        ) as exclusivity_expiration_date
    from raw.ob_exclusivity
    where upper(trim(appl_type)) = 'N'
),
exclusivity_agg as (
    select
        appl_no,
        count(*) as exclusivity_row_count,
        count(distinct exclusivity_code) as distinct_exclusivity_code_count,
        min(exclusivity_expiration_date) as earliest_exclusivity_expiration_date,
        max(exclusivity_expiration_date) as latest_exclusivity_expiration_date,
        string_agg(distinct exclusivity_expiration_date_text, '; ' order by exclusivity_expiration_date_text)
            filter (where exclusivity_expiration_date_text is not null) as exclusivity_expiration_date_texts,
        string_agg(distinct exclusivity_expiration_date_text, '; ' order by exclusivity_expiration_date_text)
            filter (
                where exclusivity_expiration_date_text is not null
                    and exclusivity_expiration_date is null
            ) as unparseable_exclusivity_expiration_date_texts,
        count(*) filter (
            where exclusivity_expiration_date_text is not null
                and exclusivity_expiration_date is null
        ) as exclusivity_unparseable_date_count
    from exclusivities
    group by appl_no
)
select
    applications.appl_no,
    coalesce(patent_agg.patent_row_count, 0) as patent_row_count,
    coalesce(patent_agg.distinct_patent_count, 0) as distinct_patent_count,
    coalesce(patent_agg.drug_substance_patent_count, 0) as drug_substance_patent_count,
    coalesce(patent_agg.drug_product_patent_count, 0) as drug_product_patent_count,
    coalesce(patent_agg.delisted_patent_count, 0) as delisted_patent_count,
    patent_agg.earliest_patent_expiration_date,
    patent_agg.latest_patent_expiration_date,
    patent_agg.patent_expiration_date_texts,
    patent_agg.unparseable_patent_expiration_date_texts,
    coalesce(patent_agg.patent_unparseable_date_count, 0) as patent_unparseable_date_count,
    coalesce(exclusivity_agg.exclusivity_row_count, 0) as exclusivity_row_count,
    coalesce(exclusivity_agg.distinct_exclusivity_code_count, 0) as distinct_exclusivity_code_count,
    exclusivity_agg.earliest_exclusivity_expiration_date,
    exclusivity_agg.latest_exclusivity_expiration_date,
    exclusivity_agg.exclusivity_expiration_date_texts,
    exclusivity_agg.unparseable_exclusivity_expiration_date_texts,
    coalesce(exclusivity_agg.exclusivity_unparseable_date_count, 0) as exclusivity_unparseable_date_count,
    case
        when patent_agg.latest_patent_expiration_date is null then exclusivity_agg.latest_exclusivity_expiration_date
        when exclusivity_agg.latest_exclusivity_expiration_date is null then patent_agg.latest_patent_expiration_date
        else greatest(patent_agg.latest_patent_expiration_date, exclusivity_agg.latest_exclusivity_expiration_date)
    end as last_protection_date
from applications
left join patent_agg
    on applications.appl_no = patent_agg.appl_no
left join exclusivity_agg
    on applications.appl_no = exclusivity_agg.appl_no;
