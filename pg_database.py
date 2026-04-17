from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

PG_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:45432/butik"
)

engine = create_engine(PG_URL)
SessionLocal = sessionmaker(bind=engine)


def get_pg():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_pg():
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS kunder (
                id      SERIAL PRIMARY KEY,
                namn    VARCHAR NOT NULL,
                email   VARCHAR UNIQUE NOT NULL,
                telefon VARCHAR
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS produkter (
                id          SERIAL PRIMARY KEY,
                namn        VARCHAR NOT NULL,
                pris        DOUBLE PRECISION NOT NULL,
                lagersaldo  INTEGER DEFAULT 0
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ordrar (
                id          SERIAL PRIMARY KEY,
                kund_id     INTEGER REFERENCES kunder(id),
                produkt_id  INTEGER REFERENCES produkter(id),
                antal       INTEGER NOT NULL,
                skapad      TIMESTAMP DEFAULT NOW()
            )
        """))
        conn.commit()


def seed_pg():
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM kunder")).scalar()
        if count > 0:
            return

        conn.execute(text("""
            INSERT INTO kunder (namn, email, telefon) VALUES
            ('Anna Svensson',   'anna@example.com',  '070-1234567'),
            ('Erik Johansson',  'erik@example.com',  '073-9876543'),
            ('Maria Lindqvist', 'maria@example.com', '076-5551234')
        """))
        conn.execute(text("""
            INSERT INTO produkter (namn, pris, lagersaldo) VALUES
            ('Laptop',      9999.0, 15),
            ('Hörlurar',     799.0, 50),
            ('Tangentbord', 1299.0, 30),
            ('Mus',          399.0, 80)
        """))
        conn.execute(text("""
            INSERT INTO ordrar (kund_id, produkt_id, antal) VALUES
            (1, 1, 1), (1, 2, 2), (2, 3, 1), (3, 4, 3)
        """))
        conn.commit()
