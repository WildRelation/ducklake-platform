# Tutorial: Skapa en Datalake med DuckLake och anslut med Python

## Introduktion

I denna tutorial bygger vi en datalake med **DuckLake** och exponerar den som ett REST API med **FastAPI**. Vi driftsätter sedan allt på **KTH Cloud** och ansluter till datalaken med en Python-klient.

### Vad är en datalake?

En datalake är ett centralt lager där data lagras i sitt råa format. Till skillnad från en traditionell databas (som PostgreSQL) lagrar en datalake data som filer — i vårt fall **Parquet-filer**. Det gör att data kan läsas av många olika verktyg och programmeringsspråk.

### Vad är DuckLake?

DuckLake är ett öppet lakehouse-format byggt ovanpå DuckDB. Det består av två delar:

- **Katalogfil** (`katalog.duckdb`) — lagrar metadata, schema och snapshots
- **Parquet-filer** (`lake/`) — lagrar den faktiska datan i kolumnformat

Varje gång du skriver data skapas en ny **snapshot** — det betyder att du kan läsa historiska versioner av datan (time travel).

---

## Förutsättningar

- Python 3.12+
- Docker
- Ett konto på [KTH Cloud](https://app.cloud.cbh.kth.se)
- Ett GitHub-konto

---

## Steg 1 — Projektstruktur

Skapa följande filstruktur:

```
butik-api/
├── main.py           # FastAPI-app (datalake-server)
├── database.py       # DuckLake-anslutning
├── seed.py           # Startdata
├── requirements.txt  # Paketberoenden
├── Dockerfile        # Container-konfiguration
├── docker-compose.yml
└── klient/
    ├── klient.py     # Python-klient
    ├── requirements.txt
    └── Dockerfile
```

---

## Steg 2 — DuckLake-anslutning

Skapa `database.py` som hanterar anslutningen till DuckLake:

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
    con.execute(f"ATTACH 'ducklake:{CATALOG_PATH}' AS butik (DATA_PATH '{DATA_PATH}')")
    return con

def init_db():
    con = get_conn()
    con.execute("""
        CREATE TABLE IF NOT EXISTS butik.kunder (
            id INTEGER, namn VARCHAR NOT NULL,
            email VARCHAR NOT NULL, telefon VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS butik.produkter (
            id INTEGER, namn VARCHAR NOT NULL,
            pris DOUBLE NOT NULL, lagersaldo INTEGER DEFAULT 0
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS butik.ordrar (
            id INTEGER, kund_id INTEGER, produkt_id INTEGER,
            antal INTEGER NOT NULL, skapad TIMESTAMP DEFAULT current_timestamp
        )
    """)
    con.close()
```

Notera att `CATALOG_PATH` och `DATA_PATH` styrs av miljövariabler — det gör att samma kod fungerar både lokalt och i molnet.

---

## Steg 3 — FastAPI-server (datalaken)

`main.py` exponerar datalaken som ett REST API med både HTML-sidor och JSON-endpoints:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from database import get_conn, init_db

app = FastAPI(title="Butik Datalake")
init_db()

# JSON API — används av klienter (Python, Java etc.)

@app.get("/api/kunder")
async def api_kunder():
    con = get_conn()
    rows = con.execute("SELECT id, namn, email, telefon FROM butik.kunder").fetchall()
    con.close()
    return [{"id": r[0], "namn": r[1], "email": r[2], "telefon": r[3]} for r in rows]

@app.post("/api/kunder", status_code=201)
async def api_ny_kund(kund: NyKund):
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.kunder").fetchone()[0]
    con.execute("INSERT INTO butik.kunder VALUES (?, ?, ?, ?)",
                [nid, kund.namn, kund.email, kund.telefon])
    con.close()
    return {"id": nid, "namn": kund.namn}
```

Fullständig kod finns i repot.

---

## Steg 4 — Dockerisera appen

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

---

## Steg 5 — GitHub Actions (automatisk CI/CD)

Skapa `.github/workflows/docker.yml`:

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

Varje gång du pushar till `main` byggs en ny Docker-image automatiskt och publiceras till GitHub Container Registry (GHCR).

---

## Steg 6 — Driftsätt på KTH Cloud

1. Gå till [app.cloud.cbh.kth.se](https://app.cloud.cbh.kth.se)
2. Skapa en ny **deployment**:
   - **Image:** `ghcr.io/wildrelation/butik-api:latest`
   - **Port:** `8000`
3. Lägg till **persistent storage**:
   - Name: `ducklake-data`
   - App path: `/app/data`
   - Storage path: `/ducklake-data`
4. Lägg till **miljövariabler**:
   - `CATALOG_PATH` = `/app/data/katalog.duckdb`
   - `DATA_PATH` = `/app/data/lake/`
5. Spara och starta deploymenten

Din datalake är nu live på:
```
https://<deployment-namn>.app.cloud.cbh.kth.se
```

---

## Steg 7 — Python-klient

Skapa `klient/klient.py` som ansluter till datalaken via HTTP:

```python
import requests
import os

DATALAKE_URL = os.getenv(
    "DATALAKE_URL",
    "https://misty-abnormally-educated.app.cloud.cbh.kth.se"
)

def hamta_kunder():
    svar = requests.get(f"{DATALAKE_URL}/api/kunder")
    svar.raise_for_status()
    return svar.json()

def skapa_kund(namn, email, telefon=None):
    svar = requests.post(f"{DATALAKE_URL}/api/kunder", json={
        "namn": namn, "email": email, "telefon": telefon
    })
    svar.raise_for_status()
    return svar.json()

if __name__ == "__main__":
    kunder = hamta_kunder()
    for k in kunder:
        print(f"{k['id']}. {k['namn']} ({k['email']})")

    ny = skapa_kund("Test Person", "test@example.se")
    print(f"Skapad: {ny}")
```

Kör klienten:

```bash
pip install requests
python klient.py
```

---

## Steg 8 — Anslutning för Java-klienter

Java-klienter ansluter på exakt samma sätt via HTTP. Tillgängliga endpoints:

| Metod | Endpoint | Beskrivning |
|-------|----------|-------------|
| GET | `/api/kunder` | Hämta alla kunder |
| GET | `/api/produkter` | Hämta alla produkter |
| GET | `/api/ordrar` | Hämta alla ordrar |
| POST | `/api/kunder` | Skapa ny kund (JSON body) |
| POST | `/api/produkter` | Skapa ny produkt (JSON body) |
| POST | `/api/ordrar` | Skapa ny order (JSON body) |
| DELETE | `/api/kunder/{id}` | Radera kund |
| DELETE | `/api/produkter/{id}` | Radera produkt |

Exempel med Java (HttpClient):

```java
HttpClient client = HttpClient.newHttpClient();
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://misty-abnormally-educated.app.cloud.cbh.kth.se/api/kunder"))
    .GET()
    .build();
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.body());
```

---

## Arkitektur

```
Python/Java-klient
      ↓ HTTP (GET/POST/DELETE)
FastAPI-server (KTH Cloud)
      ↓ läser/skriver
DuckLake
      ├── katalog.duckdb  (metadata)
      └── lake/main/
          ├── kunder/     (Parquet-filer)
          ├── produkter/  (Parquet-filer)
          └── ordrar/     (Parquet-filer)
```

---

## Varför DuckLake?

| Egenskap | DuckLake | PostgreSQL |
|----------|----------|------------|
| Kräver server | Nej | Ja |
| Dataformat | Parquet (öppet) | Binärt (proprietärt) |
| Time travel | Ja | Nej |
| Skalbarhet | S3/GCS/lokal disk | Begränsad |
| Antal deployments | 1 | 2 (app + databas) |

---

## Källkod

Fullständig källkod finns på: [github.com/WildRelation/butik-api](https://github.com/WildRelation/butik-api)
