# Assets

Bruin assets live in this directory.

Planned layers:

- `raw.*`: source ingestion from FDA Orange Book, FDA Purple Book, CMS Part D, CMS Part B, and openFDA.
- `staging.*`: cleaned, typed, deduplicated source tables.
- `marts.*`: joined and scored outputs, with `marts.drug_opportunities` as the product table and AI-facing source text base64 encoded and bounded as data.

Current raw assets:

- `raw.ob_products`
- `raw.ob_patents`
- `raw.ob_exclusivity`
- `raw.cms_part_d`
- `raw.cms_part_b`
- `raw.openfda_anda_products`
- `raw.purple_book`

Current staging assets:

- `staging.branded_drugs`
- `staging.drug_protection`
- `staging.drug_revenue`
- `staging.cms_orange_book_matches`
- `staging.cms_orange_book_match_diagnostics`
- `staging.anda_competition`
- `staging.biologic_products`
- `staging.biosimilar_competition`
- `staging.cms_part_b_biologic_matches`
- `staging.cms_part_b_biologic_match_diagnostics`
- `staging.drug_descriptions`

Current mart assets:

- `marts.drug_opportunities`
- `marts.site_opportunities`
