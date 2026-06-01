"""@bruin
name: raw.ob_exclusivity
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace
columns:
  - name: appl_type
    type: varchar
    description: FDA application type from Orange Book exclusivity.txt.
  - name: appl_no
    type: varchar
    description: FDA application number as provided by Orange Book exclusivity.txt.
  - name: product_no
    type: varchar
    description: FDA product number as provided by Orange Book exclusivity.txt.
  - name: exclusivity_code
    type: varchar
    description: FDA exclusivity code.
  - name: exclusivity_date
    type: varchar
    description: Raw exclusivity expiry text; date parsing is intentionally deferred to staging.
@bruin"""

from assets.raw._orange_book import EXCLUSIVITY_COLUMNS, read_orange_book_file


def materialize() -> list[dict[str, str]]:
    return read_orange_book_file("exclusivity.txt", EXCLUSIVITY_COLUMNS)
