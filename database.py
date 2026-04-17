import duckdb
import os

CATALOG_PATH = os.getenv("CATALOG_PATH", "/app/data/katalog.duckdb")
DATA_PATH    = os.getenv("DATA_PATH",    "/app/data/lake/")


def get_conn():
    os.makedirs(DATA_PATH, exist_ok=True)
    con = duckdb.connect()
    con.execute("LOAD ducklake")
    con.execute(f"ATTACH 'ducklake:{CATALOG_PATH}' AS butik (DATA_PATH '{DATA_PATH}')")
    return con


def init_db():
    con = get_conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS butik.kunder (
            id      INTEGER,
            namn    VARCHAR NOT NULL,
            email   VARCHAR NOT NULL,
            telefon VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS butik.produkter (
            id         INTEGER,
            namn       VARCHAR NOT NULL,
            pris       DOUBLE  NOT NULL,
            lagersaldo INTEGER
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS butik.ordrar (
            id         INTEGER,
            kund_id    INTEGER,
            produkt_id INTEGER,
            antal      INTEGER NOT NULL,
            skapad     TIMESTAMP DEFAULT current_timestamp
        )
    """)
    con.close()
