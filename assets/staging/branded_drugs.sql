/* @bruin
name: staging.branded_drugs
type: duckdb.sql
materialization:
  type: table

depends:
  - raw.ob_products

columns:
  - name: branded_product_key
    type: varchar
    description: Stable NDA product key built from application and product number.
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: appl_no
    type: varchar
    description: FDA NDA application number.
    checks:
      - name: not_null
  - name: product_no
    type: varchar
    description: FDA Orange Book product number within the application.
    checks:
      - name: not_null
  - name: appl_type
    type: varchar
    description: FDA application type. Phase 04 keeps only NDA products.
    checks:
      - name: not_null
  - name: trade_name
    type: varchar
    description: Branded trade name from Orange Book.
    checks:
      - name: not_null
  - name: trade_name_key
    type: varchar
    description: Lowercase alphanumeric join key for the trade name.
    checks:
      - name: not_null
  - name: ingredient
    type: varchar
    description: Active ingredient text from Orange Book.
    checks:
      - name: not_null
  - name: ingredient_key
    type: varchar
    description: Lowercase alphanumeric join key for the active ingredient.
    checks:
      - name: not_null
  - name: applicant
    type: varchar
    description: Short applicant name from Orange Book.
  - name: applicant_full_name
    type: varchar
    description: Full applicant name from Orange Book.
  - name: dosage_form_route
    type: varchar
    description: Dosage form and route text from Orange Book.
  - name: strength
    type: varchar
    description: Product strength text from Orange Book.
  - name: marketing_status
    type: varchar
    description: Orange Book marketing status, usually RX, OTC, or DISCN.
  - name: approval_date_text
    type: varchar
    description: Raw Orange Book approval date text.
  - name: approval_date
    type: date
    description: Parsed approval date when Orange Book provides an exact date.
  - name: approval_date_parse_status
    type: varchar
    description: "Date parse status: parsed, legacy_pre_1982, blank, or unparseable."
  - name: rld
    type: varchar
    description: Reference listed drug flag from Orange Book.
  - name: rs
    type: varchar
    description: Reference standard flag from Orange Book.
  - name: is_reference_listed_drug
    type: boolean
    description: True when Orange Book RLD flag is Yes.
  - name: is_reference_standard
    type: boolean
    description: True when Orange Book RS flag is Yes.

custom_checks:
  - name: only NDA products are staged
    query: select count(*) from staging.branded_drugs where appl_type <> 'N'
    value: 0
  - name: product keys are unique
    query: select count(*) from (select branded_product_key from staging.branded_drugs group by 1 having count(*) > 1)
    value: 0
  - name: reference flags use accepted values
    query: select count(*) from staging.branded_drugs where rld not in ('Yes', 'No') or rs not in ('Yes', 'No')
    value: 0
  - name: marketing status uses accepted values
    query: select count(*) from staging.branded_drugs where marketing_status not in ('RX', 'OTC', 'DISCN')
    value: 0
  - name: approval date parse status uses accepted values
    query: select count(*) from staging.branded_drugs where approval_date_parse_status not in ('parsed', 'legacy_pre_1982', 'blank', 'unparseable')
    value: 0
@bruin */

with cleaned as (
    select
        nullif(trim(appl_no), '') as appl_no,
        nullif(trim(product_no), '') as product_no,
        upper(trim(appl_type)) as appl_type,
        nullif(trim(trade_name), '') as trade_name,
        nullif(trim(ingredient), '') as ingredient,
        nullif(trim(applicant), '') as applicant,
        nullif(trim(applicant_full_name), '') as applicant_full_name,
        nullif(trim(df_route), '') as dosage_form_route,
        nullif(trim(strength), '') as strength,
        upper(nullif(trim(type), '')) as marketing_status,
        nullif(trim(approval_date), '') as approval_date_text,
        regexp_replace(
            nullif(regexp_replace(trim(approval_date), '[[:space:]]+', ' ', 'g'), ''),
            '^([A-Za-z]+) ([0-9]), ([0-9]{4})$',
            '\1 0\2, \3'
        ) as approval_date_parse_text,
        case
            when upper(nullif(trim(rld), '')) = 'YES' then 'Yes'
            when upper(nullif(trim(rld), '')) = 'NO' then 'No'
            else nullif(trim(rld), '')
        end as rld,
        case
            when upper(nullif(trim(rs), '')) = 'YES' then 'Yes'
            when upper(nullif(trim(rs), '')) = 'NO' then 'No'
            else nullif(trim(rs), '')
        end as rs
    from raw.ob_products
),
normalized as (
    select
        concat(appl_no, '-', product_no) as branded_product_key,
        appl_no,
        product_no,
        appl_type,
        trade_name,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(coalesce(trade_name, ''), '[^A-Za-z0-9]+', ' ', 'g'),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as trade_name_key,
        ingredient,
        nullif(
            trim(
                lower(
                    regexp_replace(
                        regexp_replace(coalesce(ingredient, ''), '[^A-Za-z0-9]+', ' ', 'g'),
                        '[[:space:]]+',
                        ' ',
                        'g'
                    )
                )
            ),
            ''
        ) as ingredient_key,
        applicant,
        applicant_full_name,
        dosage_form_route,
        strength,
        marketing_status,
        approval_date_text,
        cast(try_strptime(approval_date_parse_text, ['%b %d, %Y', '%B %d, %Y']) as date) as approval_date,
        case
            when approval_date_text is null then 'blank'
            when approval_date_parse_text = 'Approved Prior to Jan 1, 1982' then 'legacy_pre_1982'
            when try_strptime(approval_date_parse_text, ['%b %d, %Y', '%B %d, %Y']) is not null then 'parsed'
            else 'unparseable'
        end as approval_date_parse_status,
        rld,
        rs,
        upper(rld) = 'YES' as is_reference_listed_drug,
        upper(rs) = 'YES' as is_reference_standard
    from cleaned
    where appl_type = 'N'
        and appl_no is not null
        and product_no is not null
)
select *
from normalized;
