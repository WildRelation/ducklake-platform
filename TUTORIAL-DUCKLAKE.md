# Tutorial: Bygg och driftsätt en DuckLake Datalake

## Introduktion

I denna tutorial bygger vi en datalake med **DuckLake** och exponerar den som ett REST API med **FastAPI**. Vi driftsätter allt på **KTH Cloud**.

När du är klar har du en datalake som är nåbar via HTTP — du kan sedan ansluta till den med Python (se [TUTORIAL-PYTHON.md](TUTORIAL-PYTHON.md)) eller Java (se [TUTORIAL-JAVA.md](TUTORIAL-JAVA.md)).

### Vad är en datalake?

En datalake är ett centralt lager där data lagras i sitt råa format. Till skillnad från en traditionell databas (som PostgreSQL) lagrar en datalake data som filer — i vårt fall **Parquet-filer**. Det gör att data kan läsas av många olika verktyg och programmeringsspråk.

### Vad är DuckLake?

DuckLake är ett öppet lakehouse-format byggt ovanpå DuckDB. Det består av två delar:

- **Katalogfil** (`katalog.duckdb`) — lagrar metadata, schema och snapshots
- **Parquet-filer** (`lake/`) — lagrar den faktiska datan i kolumnformat

Varje gång du skriver data skapas en ny **snapshot** — det betyder att du kan läsa historiska versioner av datan (time travel).

### Varför behövs FastAPI?

DuckLake är ingen server — det är bara filer på disk. FastAPI fungerar som ett lager ovanpå DuckLake som exponerar datan via HTTP så att andra program (Python, Java etc.) kan kommunicera med datalaken.

---

## Förutsättningar

- Python 3.12+
- Docker
- Ett konto på [KTH Cloud](https://app.cloud.cbh.kth.se)
- Ett GitHub-konto

---

## Arkitektur

```
<klient>               →HTTP→        <datalake-deployment>
                                      (FastAPI + DuckLake)
                                              ↓
                                      /app/data (persistent volym)
                                      ├── katalog.duckdb
                                      └── lake/main/
                                          ├── tabell1/   ← Parquet
                                          ├── tabell2/   ← Parquet
                                          └── tabell3/   ← Parquet
```

---

## Steg 1 — Projektstruktur

Skapa ett nytt GitHub-repo och klona det lokalt. Skapa sedan följande filstruktur:

```
<repo-namn>/
├── main.py            # FastAPI REST API
├── database.py        # DuckLake-anslutning
├── requirements.txt
├── Dockerfile
└── .github/
    └── workflows/
        └── docker.yml
```

---

## Steg 2 — DuckLake-anslutning

Skapa `database.py`:

```python
import duckdb
import os

CATALOG_PATH = os.getenv("CATALOG_PATH", "./data/katalog.duckdb")
DATA_PATH    = os.getenv("DATA_PATH",    "./data/lake/")

def get_conn():
    os.makedirs(DATA_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
    con = duckdb.connect()
    con.execute("LOAD ducklake")
    con.execute(f"ATTACH 'ducklake:{CATALOG_PATH}' AS lake (DATA_PATH '{DATA_PATH}')")
    return con

def init_db():
    con = get_conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS lake.produkter (
            id INTEGER, namn VARCHAR NOT NULL,
            pris DOUBLE NOT NULL
        )
    """)
    con.close()
```

`CATALOG_PATH` och `DATA_PATH` styrs av miljövariabler — samma kod fungerar lokalt och i molnet.

---

## Steg 3 — FastAPI REST API

Skapa `main.py`:

```python
import os
import secrets
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_conn, init_db

API_KEY = os.getenv("API_KEY", "change-me")

def verify_key(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key.encode(), API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Ogiltig API-nyckel")

app = FastAPI(title="Min Datalake")
init_db()

class NyProdukt(BaseModel):
    namn: str
    pris: float

# GET — öppen för alla
@app.get("/api/produkter")
async def get_produkter():
    con = get_conn()
    rows = con.execute("SELECT id, namn, pris FROM lake.produkter ORDER BY id").fetchall()
    con.close()
    return [{"id": r[0], "namn": r[1], "pris": r[2]} for r in rows]

# POST — kräver API-nyckel
@app.post("/api/produkter", status_code=201, dependencies=[Depends(verify_key)])
async def ny_produkt(p: NyProdukt):
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM lake.produkter").fetchone()[0]
    con.execute("INSERT INTO lake.produkter VALUES (?, ?, ?)", [nid, p.namn, p.pris])
    con.close()
    return {"id": nid, "namn": p.namn, "pris": p.pris}

# DELETE — kräver API-nyckel
@app.delete("/api/produkter/{pid}", dependencies=[Depends(verify_key)])
async def radera_produkt(pid: int):
    con = get_conn()
    con.execute("DELETE FROM lake.produkter WHERE id = ?", [pid])
    con.close()
    return {"deleted": pid}
```

Fullständig källkod finns i repot: [github.com/WildRelation/ducklake-platform](https://github.com/WildRelation/ducklake-platform)

---

## Steg 4 — Autentisering

Skriv-operationer (POST/DELETE) skyddas med en API-nyckel i headern `X-API-Key`. GET-anrop är öppna för alla.

**Varför miljövariabel och inte hårdkodad nyckel?**
Om du skriver nyckeln i koden och pushar till GitHub kan vem som helst läsa den. Sätt den istället som miljövariabel i KTH Cloud (se Steg 6).

```python
API_KEY = os.getenv("API_KEY", "change-me")
```

---

## Steg 5 — Dockerisera och pusha med GitHub Actions

`Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python3 -c "import duckdb; con = duckdb.connect(); con.execute('INSTALL ducklake')"
COPY . .
ENV CATALOG_PATH=/app/data/katalog.duckdb
ENV DATA_PATH=/app/data/lake/
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`requirements.txt`:

```
fastapi==0.136.0
uvicorn==0.44.0
duckdb==1.5.2
pytz
python-multipart==0.0.20
```

`.github/workflows/docker.yml`:

```yaml
name: Build and push Docker image
on:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Set lowercase image name
        run: echo "IMAGE=ghcr.io/$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]'):latest" >> $GITHUB_ENV
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ env.IMAGE }}
```

Pusha koden till `main` — GitHub Actions bygger och pushar Docker-imagen automatiskt.

---

## Steg 6 — Driftsätt på KTH Cloud

1. Gå till [app.cloud.cbh.kth.se](https://app.cloud.cbh.kth.se) → **New deployment**
2. Fyll i:
   - **Image:** `ghcr.io/<ditt-github-användarnamn>/<repo-namn>:latest`
   - **Port:** `8000`
   - **Visibility:** Public
3. Lägg till **persistent storage**:
   - Name: `ducklake-data`
   - App path: `/app/data`
   - Storage path: `/ducklake-data`
4. Lägg till **miljövariabler**:
   - `CATALOG_PATH` = `/app/data/katalog.duckdb`
   - `DATA_PATH` = `/app/data/lake/`
   - `API_KEY` = `<ditt-hemliga-lösenord>` ← **välj ett starkt lösenord**
5. Spara — datalaken är nu live på `https://<deployment-namn>.app.cloud.cbh.kth.se`

> **Varför persistent storage?** DuckLake lagrar data som filer. Utan en persistent volym försvinner all data varje gång containern startas om.

Verifiera att allt fungerar:
```
https://<deployment-namn>.app.cloud.cbh.kth.se/api/produkter
```

Du ska se en JSON-lista. API-dokumentation finns på `/docs`.

---

## Varför DuckLake?

| Egenskap | DuckLake | PostgreSQL |
|----------|----------|------------|
| Kräver server | Nej | Ja |
| Dataformat | Parquet (öppet) | Binärt (proprietärt) |
| Time travel | Ja | Nej |
| Skalbarhet | S3/GCS/lokal disk | Begränsad |
| Antal deployments | 1 | 2 (app + databas) |
| Kan läsas av | Python, Java, Spark, Pandas... | Kräver PostgreSQL-klient |

---

## Nästa steg

- Anslut med Python → [TUTORIAL-PYTHON.md](TUTORIAL-PYTHON.md)
- Anslut med Java → [TUTORIAL-JAVA.md](TUTORIAL-JAVA.md)

Exempel på live datalake: [misty-abnormally-educated.app.cloud.cbh.kth.se](https://misty-abnormally-educated.app.cloud.cbh.kth.se)
