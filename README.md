# Lapse

**Which drugs should a generic manufacturer file on next — ranked, off public data.**

Between 2025 and 2030, branded drugs worth an estimated $200B+ in annual sales lose patent
protection — the largest patent cliff in pharmaceutical history. Generic and biosimilar makers have
to decide which of those drugs to pursue with limited resources, and today they do it by hand,
stitching together government databases.

Lapse turns that manual research into a ranked, scored intelligence layer. It currently joins FDA
Orange Book, FDA Purple Book, CMS Medicare Part D and Part B spending data, openFDA Drugs@FDA ANDA
signals, openFDA Drug Labeling descriptions, and biosimilar competition signals, then scores small
molecules and biologics in one cross-modality opportunity table.

Built end-to-end on [Bruin](https://getbruin.com).

## What it does
1. **Ingests** the FDA Orange Book (products, patents, exclusivity), FDA Purple Book biologics,
   CMS Part D and Part B spending, openFDA ANDA products, and openFDA label descriptions.
2. **Joins and scores** small molecules and biologics on market size, protection-expiry timing,
   match quality, and modality-specific competition density.
3. **Ranks** the universe into a single `drug_opportunities` table.
4. **Answers** business-development questions over that table through Bruin's AI data analyst.

## Bruin features used
- **Ingestion** — Python assets that download and parse the Orange Book ZIP, Purple Book CSV,
  CMS Part D and Part B CSVs, and openFDA Drugs@FDA API.
- **Transformation** — DuckDB SQL assets for cleaning, name normalization, the join, and scoring.
- **Quality checks** — `not_null`, `unique`, `accepted_values`, and a custom score-range check.
- **Orchestration & lineage** — one `bruin run .` runs the whole DAG in order; lineage shows the flow.
- **AI data analyst** — Bruin MCP + Claude Code answering natural-language questions on the output.

## Pipeline
```
raw.ob_products ─┐
raw.ob_patents ──┼─► staging.branded_drugs / staging.drug_protection ─┐
raw.ob_exclusivity ┘                                                   │
raw.cms_part_d ─┐
raw.cms_part_b ─┴──────► staging.drug_revenue ─► staging.cms_orange_book_matches ─┤
raw.openfda_anda_products ─► staging.anda_competition ───────────────────────────┘
raw.purple_book ──────► staging.biologic_products ─► staging.biosimilar_competition
                                ▲
                                └──── staging.cms_part_b_biologic_matches / diagnostics
                                                                               │
                                                                               ▼
                                                                 marts.drug_opportunities ─► AI analyst
                                                                               │
                                              staging.drug_descriptions ◄──────┘
                                                                               │
                                                                               ▼
                                                                  marts.site_opportunities ─► site/data/opportunities.json
```

## Run it
```bash
curl -LsSf https://getbruin.com/install/cli | sh
cp .bruin.yml.example .bruin.yml
bruin validate .
bruin run --workers 1 .
```
DuckDB backend, zero external setup — all data sources are public and unauthenticated.

The FDA Orange Book raw assets download the official ZIP from FDA and materialize the three
tilde-delimited files into DuckDB tables. The CMS Part D and Part B raw assets download the official
annual 2023 spending CSVs from data.cms.gov and materialize them into `raw.cms_part_d` and
`raw.cms_part_b`. The openFDA raw asset pages through Drugs@FDA ANDA applications and flattens
product-level generic competition signals into `raw.openfda_anda_products`. The Purple Book raw asset
resolves the latest official FDA CSV from the Purple Book downloads page and materializes the complete
all-products table into `raw.purple_book`, including reference-product grouping and
biosimilar/interchangeable flags for biologics scoring. The label enrichment asset queries the
openFDA Drug Labeling API for the exported opportunity window and keeps only nullable class,
mechanism, and first-clause indication text for the local site. CMS, openFDA, and Purple Book
free-text fields are sanitized, length-capped, base64 encoded where exposed to the mart, and wrapped
in `DATA START` / `DATA END` boundaries before they can reach the AI-facing mart.

The staging layer filters Orange Book products to branded NDA drugs, parses patent and exclusivity
dates, normalizes CMS Part D and Part B brand/generic names into one revenue table, and publishes
match diagnostics for the lossy CMS-to-Orange-Book and CMS Part B-to-Purple-Book name joins. It also
aggregates `staging.anda_competition` by matching ANDA products to branded applications on normalized
ingredient and dosage route, and `staging.biosimilar_competition` by counting Purple Book 351(k)
products per reference biologic.

The first mart, `marts.drug_opportunities`, rolls those staged tables into one ranked
cross-modality table with market size, protection timing, match quality, generic or biosimilar
competition density, and a final 0-100 opportunity score. Market size is normalized inside each
modality so biologic spending does not hide small-molecule opportunities.

`marts.site_opportunities` exports the top opportunity window to `site/data/opportunities.json`.
The static `/site` dashboard reads that file directly, so opening the site after a Bruin run shows
real pipeline output rather than sample data.

Raw source text is stored as data, not SQL. Pipeline SQL assets are static transformations over
columns, and any ad-hoc or application consumer must use parameterized queries instead of
concatenating CMS, FDA, or openFDA text values into SQL strings.


## A note on the data
CMS keys on drug names and the Orange Book keys on application numbers, so the join between revenue
and patents is name-based and intentionally lossy — unmatched rows are expected and the match rate is
logged. The opportunity score weights are a deliberate judgment call, documented at the top of the
scoring SQL, not a claim of ground truth. The ANDA competition match is also normalized and lossy:
a missing openFDA match receives the low-competition score for this proof of concept, but it is not
evidence that no generic competition exists.

## Status
A focused proof of concept being built for the Bruin project competition. Scope is deliberately
limited to FDA Orange Book, FDA Purple Book raw coverage, CMS Part D and Part B spending, openFDA ANDA
competition density, a simple local dashboard, and the Bruin AI analyst demo. CourtListener
litigation, USPTO/FTC patent challenges, auth, cloud deploy, and alerting are out of scope for this
build.
