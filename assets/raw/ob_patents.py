"""@bruin
name: raw.ob_patents
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace
columns:
  - name: appl_type
    type: varchar
    description: FDA application type from Orange Book patent.txt.
  - name: appl_no
    type: varchar
    description: FDA application number as provided by Orange Book patent.txt.
  - name: product_no
    type: varchar
    description: FDA product number as provided by Orange Book patent.txt.
  - name: patent_no
    type: varchar
    description: Patent number as submitted to FDA.
  - name: patent_expire_date_text
    type: varchar
    description: Raw patent expiry text; date parsing is intentionally deferred to staging.
  - name: drug_substance_flag
    type: varchar
    description: FDA drug substance patent flag from Orange Book patent.txt.
  - name: drug_product_flag
    type: varchar
    description: FDA drug product patent flag from Orange Book patent.txt.
  - name: patent_use_code
    type: varchar
    description: FDA patent use code from Orange Book patent.txt.
  - name: delist_flag
    type: varchar
    description: FDA delist flag from Orange Book patent.txt.
  - name: submission_date
    type: varchar
    description: Raw patent submission date text from Orange Book patent.txt.
@bruin"""

from assets.raw._orange_book import PATENT_COLUMNS, read_orange_book_file


def materialize() -> list[dict[str, str]]:
    return read_orange_book_file("patent.txt", PATENT_COLUMNS)
