import duckdb

DB_PATH = "butik.duckdb"


def get_conn():
    return duckdb.connect(DB_PATH)


def init_db():
    con = get_conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS kunder (
            id      INTEGER PRIMARY KEY,
            namn    VARCHAR NOT NULL,
            email   VARCHAR UNIQUE NOT NULL,
            telefon VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS produkter (
            id          INTEGER PRIMARY KEY,
            namn        VARCHAR NOT NULL,
            pris        DOUBLE NOT NULL,
            lagersaldo  INTEGER DEFAULT 0
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS ordrar (
            id          INTEGER PRIMARY KEY,
            kund_id     INTEGER REFERENCES kunder(id),
            produkt_id  INTEGER REFERENCES produkter(id),
            antal       INTEGER NOT NULL,
            skapad      TIMESTAMP DEFAULT current_timestamp
        )
    """)
    con.close()
