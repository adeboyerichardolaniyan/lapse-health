"""@bruin
name: raw.ob_products
image: python:3.13
connection: duckdb-default
materialization:
  type: table
  strategy: create+replace
columns:
  - name: ingredient
    type: varchar
    description: Active ingredient text from Orange Book products.txt.
  - name: df_route
    type: varchar
    description: Dosage form and route from Orange Book products.txt.
  - name: trade_name
    type: varchar
    description: FDA trade name from Orange Book products.txt.
  - name: applicant
    type: varchar
    description: Short applicant name from Orange Book products.txt.
  - name: strength
    type: varchar
    description: Product strength text from Orange Book products.txt.
  - name: appl_type
    type: varchar
    description: FDA application type; N means NDA/innovator and A means ANDA/generic.
  - name: appl_no
    type: varchar
    description: FDA application number as provided by Orange Book products.txt.
  - name: product_no
    type: varchar
    description: FDA product number as provided by Orange Book products.txt.
  - name: te_code
    type: varchar
    description: FDA therapeutic equivalence code from Orange Book products.txt.
  - name: approval_date
    type: varchar
    description: Raw product approval date text from Orange Book products.txt.
  - name: rld
    type: varchar
    description: Reference listed drug flag from Orange Book products.txt.
  - name: rs
    type: varchar
    description: Reference standard flag from Orange Book products.txt.
  - name: type
    type: varchar
    description: Product marketing type from Orange Book products.txt.
  - name: applicant_full_name
    type: varchar
    description: Full applicant name from Orange Book products.txt.
@bruin"""

from assets.raw._orange_book import PRODUCT_COLUMNS, read_orange_book_file


def materialize() -> list[dict[str, str]]:
    return read_orange_book_file("products.txt", PRODUCT_COLUMNS)
