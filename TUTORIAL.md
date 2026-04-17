# Tutorial: Skapa en Datalake med DuckLake och anslut med Python

## Introduktion

I denna tutorial bygger vi en datalake med **DuckLake** och exponerar den som ett REST API med **FastAPI**. Vi driftsätter allt på **KTH Cloud** med två separata deployments — en för datalaken och en för Python-klienten som ansluter till den.

### Vad är en datalake?

En datalake är ett centralt lager där data lagras i sitt råa format. Till skillnad från en traditionell databas (som PostgreSQL) lagrar en datalake data som filer — i vårt fall **Parquet-filer**. Det gör att data kan läsas av många olika verktyg och programmeringsspråk.

### Vad är DuckLake?

DuckLake är ett öppet lakehouse-format byggt ovanpå DuckDB. Det består av två delar:

- **Katalogfil** (`katalog.duckdb`) — lagrar metadata, schema och snapshots
- **Parquet-filer** (`lake/`) — lagrar den faktiska datan i kolumnformat

Varje gång du skriver data skapas en ny **snapshot** — det betyder att du kan läsa historiska versioner av datan (time travel).

### Varför behövs FastAPI?

DuckLake är ingen server — det är bara filer på disk. Det kan inte ta emot nätverksanslutningar på egen hand. FastAPI fungerar som ett lager ovanpå DuckLake som exponerar datan via HTTP så att andra program (Python, Java etc.) kan kommunicera med datalaken.

---

## Förutsättningar

- Python 3.12+
- Docker
- Ett konto på [KTH Cloud](https://app.cloud.cbh.kth.se)
- Ett GitHub-konto

---

## Arkitektur

```
<klient-deployment>                  <datalake-deployment>
(Python-klient)        →HTTP→        (Datalake — FastAPI + DuckLake)
                                              ↓
                                      /app/data (persistent volym)
                                      ├── katalog.duckdb
                                      └── lake/main/
                                          ├── kunder/    ← Parquet
                                          ├── produkter/ ← Parquet
                                          └── ordrar/    ← Parquet
```

---

## Steg 1 — Projektstruktur

Skapa ett nytt GitHub-repo och klona det lokalt. Skapa sedan följande filstruktur:

```
butik-api/
├── main.py            # FastAPI-app (datalaken)
├── database.py        # DuckLake-anslutning
├── requirements.txt
├── Dockerfile
├── .github/
│   └── workflows/
│       ├── docker.yml         # Bygger datalake-imagen
│       └── docker-klient.yml  # Bygger klient-imagen
└── klient/
    ├── klient.py      # Python-klienten
    ├── requirements.txt
    └── Dockerfile
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

`CATALOG_PATH` och `DATA_PATH` styrs av miljövariabler — samma kod fungerar lokalt och i molnet.

---

## Steg 3 — FastAPI-server (datalaken)

`main.py` exponerar datalaken som ett REST API. Här är grundstrukturen:

```python
import os
import secrets
from fastapi import FastAPI, Form, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
from database import get_conn, init_db

API_KEY = os.getenv("API_KEY", "change-me")

def kontrollera_nyckel(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key.encode(), API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Ogiltig API-nyckel")

app = FastAPI(title="Butik Datalake")
init_db()

class NyKund(BaseModel):
    namn: str
    email: str
    telefon: Optional[str] = None

# GET — öppen för alla
@app.get("/api/kunder")
async def api_kunder():
    con = get_conn()
    rows = con.execute("SELECT id, namn, email, telefon FROM butik.kunder ORDER BY id").fetchall()
    con.close()
    return [{"id": r[0], "namn": r[1], "email": r[2], "telefon": r[3]} for r in rows]

# POST — kräver API-nyckel
@app.post("/api/kunder", status_code=201, dependencies=[Depends(kontrollera_nyckel)])
async def api_ny_kund(kund: NyKund):
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.kunder").fetchone()[0]
    con.execute("INSERT INTO butik.kunder VALUES (?, ?, ?, ?)",
                [nid, kund.namn, kund.email, kund.telefon])
    con.close()
    return {"id": nid, "namn": kund.namn, "email": kund.email}

# DELETE — kräver API-nyckel
@app.delete("/api/kunder/{kund_id}", dependencies=[Depends(kontrollera_nyckel)])
async def api_radera_kund(kund_id: int):
    con = get_conn()
    con.execute("DELETE FROM butik.kunder WHERE id = ?", [kund_id])
    con.close()
    return {"deleted": kund_id}
```

Fullständig kod (inkl. produkter, ordrar, HTML-sidor) finns i repot.

---

## Steg 4 — Autentisering

Skriv-operationer (POST/DELETE) skyddas med en API-nyckel som skickas i headern `X-API-Key`. GET-anrop är öppna för alla — de används av klienter som bara läser data.

### Varför miljövariabel och inte hårdkodad nyckel?

Nyckeln sätts via miljövariabeln `API_KEY` — **aldrig** direkt i koden. Om du skriver nyckeln i koden och pushar till GitHub kan vem som helst läsa den. Med en miljövariabel stannar hemligheten i molnplattformen.

```python
API_KEY = os.getenv("API_KEY", "change-me")
```

`"change-me"` är bara en placeholder. I produktion sätter du `API_KEY` som miljövariabel i KTH Cloud (se Steg 8).

### Endpoints som kräver API-nyckel

| Metod | Endpoint | Kräver nyckel |
|-------|----------|---------------|
| GET | `/api/kunder` | Nej |
| GET | `/api/produkter` | Nej |
| GET | `/api/ordrar` | Nej |
| POST | `/api/kunder` | **Ja** |
| POST | `/api/produkter` | **Ja** |
| POST | `/api/ordrar` | **Ja** |
| DELETE | `/api/kunder/{id}` | **Ja** |
| DELETE | `/api/produkter/{id}` | **Ja** |

---

## Steg 5 — Dockerisera datalaken

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

## Steg 6 — Python-klienten

`klient/klient.py` är en FastAPI-app som hämtar data från datalaken och visar den i en webbsida:

```python
import requests
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

DATALAKE_URL = os.getenv("DATALAKE_URL", "http://localhost:8000")

app = FastAPI(title="Datalake Klient")

def hamta(endpoint: str):
    svar = requests.get(f"{DATALAKE_URL}{endpoint}", timeout=5)
    svar.raise_for_status()
    return svar.json()

@app.get("/", response_class=HTMLResponse)
async def index():
    kunder    = hamta("/api/kunder")
    produkter = hamta("/api/produkter")
    ordrar    = hamta("/api/ordrar")
    # Bygger HTML-tabell och returnerar...
```

`klient/requirements.txt`:

```
fastapi==0.136.0
uvicorn==0.44.0
requests==2.32.3
```

`klient/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY klient.py .
EXPOSE 8001
CMD ["uvicorn", "klient:app", "--host", "0.0.0.0", "--port", "8001"]
```

> **OBS:** `DATALAKE_URL` sätts som miljövariabel i KTH Cloud (se Steg 9) — hårdkoda inte URL:en i Dockerfile.

---

## Steg 7 — GitHub Actions (CI/CD)

Skapa två workflows — en för datalaken och en för klienten.

`.github/workflows/docker.yml` (datalaken):

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

`.github/workflows/docker-klient.yml` (klienten):

```yaml
name: Build and push klient image
on:
  push:
    branches: [main]
    paths:
      - klient/**
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - name: Set lowercase image name
        run: echo "IMAGE=ghcr.io/$(echo '${{ github.repository }}' | tr '[:upper:]' '[:lower:]')/klient:latest" >> $GITHUB_ENV
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./klient
          push: true
          tags: ${{ env.IMAGE }}
```

Pusha koden till `main` — GitHub Actions bygger automatiskt Docker-bilderna och laddar upp dem till GHCR.

---

## Steg 8 — SSH-nyckel till KTH Cloud

KTH Cloud använder SSH-nycklar för att autentisera deployments. Generera en nyckel och lägg till den i portalen:

```bash
ssh-keygen -t ed25519 -C "din@email.com"
cat ~/.ssh/id_ed25519.pub
```

Kopiera utskriften och lägg till den under **Account → SSH Keys** på [app.cloud.cbh.kth.se](https://app.cloud.cbh.kth.se).

---

## Steg 9 — Driftsätt datalaken på KTH Cloud

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
   - `API_KEY` = `<ditt-hemliga-lösenord>` ← **välj ett starkt lösenord, skriv det inte i koden**
5. Spara — datalaken är nu live på `https://<deployment-namn>.app.cloud.cbh.kth.se`

> **Varför persistent storage?** DuckLake lagrar data som filer. Utan en persistent volym försvinner all data varje gång containern startas om.

---

## Steg 10 — Driftsätt klienten på KTH Cloud

1. Skapa en ny deployment:
   - **Image:** `ghcr.io/<ditt-github-användarnamn>/<repo-namn>/klient:latest`
   - **Port:** `8001`
   - **Visibility:** Public
2. Lägg till miljövariabel:
   - `DATALAKE_URL` = `https://<datalake-deployment-namn>.app.cloud.cbh.kth.se`
3. **Ingen persistent storage behövs** — klienten lagrar ingenting lokalt

Klienten är nu live och hämtar data från datalaken:
```
https://<klient-deployment-namn>.app.cloud.cbh.kth.se
```

---

## Steg 11 — Anslutning för Java-klienter

Java-klienter ansluter via HTTP mot datalakens API. GET-anrop behöver ingen nyckel. POST/DELETE kräver headern `X-API-Key`.

```java
HttpClient client = HttpClient.newHttpClient();

// Hämta alla kunder (ingen nyckel krävs)
HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://<datalake-deployment>.app.cloud.cbh.kth.se/api/kunder"))
    .GET()
    .build();
HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
System.out.println(response.body());

// Skapa ny kund (kräver API-nyckel)
String json = "{\"namn\":\"Java Klient\",\"email\":\"java@example.com\"}";
HttpRequest postRequest = HttpRequest.newBuilder()
    .uri(URI.create("https://<datalake-deployment>.app.cloud.cbh.kth.se/api/kunder"))
    .header("Content-Type", "application/json")
    .header("X-API-Key", "ditt-hemliga-lösenord")
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();
HttpResponse<String> postResponse = client.send(postRequest, HttpResponse.BodyHandlers.ofString());
System.out.println(postResponse.body());

// Radera kund (kräver API-nyckel)
HttpRequest deleteRequest = HttpRequest.newBuilder()
    .uri(URI.create("https://<datalake-deployment>.app.cloud.cbh.kth.se/api/kunder/1"))
    .header("X-API-Key", "ditt-hemliga-lösenord")
    .DELETE()
    .build();
HttpResponse<String> deleteResponse = client.send(deleteRequest, HttpResponse.BodyHandlers.ofString());
System.out.println(deleteResponse.body());
```

---

## Varför DuckLake?

| Egenskap | DuckLake | PostgreSQL |
|----------|----------|------------|
| Kräver server | Nej | Ja |
| Dataformat | Parquet (öppet) | Binärt (proprietärt) |
| Time travel | Ja | Nej |
| Skalbarhet | S3/GCS/lokal disk | Begränsad |
| Antal deployments | 1 (datalaken) | 2 (app + databas) |
| Kan läsas av | Python, Java, Spark, Pandas... | Kräver PostgreSQL-klient |

---

## Källkod

Fullständig källkod: [github.com/WildRelation/butik-api](https://github.com/WildRelation/butik-api)

Live datalake: [misty-abnormally-educated.app.cloud.cbh.kth.se](https://misty-abnormally-educated.app.cloud.cbh.kth.se)

Live klient: [python-deployment.app.cloud.cbh.kth.se](https://python-deployment.app.cloud.cbh.kth.se)
