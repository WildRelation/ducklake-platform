# Tutorial: Anslut till en DuckLake Datalake med Python

## Introduktion

I denna tutorial bygger vi en **Python-klient** som ansluter till en datalake och hämtar data via HTTP. Klienten är en FastAPI-app som visar datan i en webbsida.

> **Förutsättning:** Du behöver en driftsatt datalake. Följ [TUTORIAL-DUCKLAKE.md](TUTORIAL-DUCKLAKE.md) för att sätta upp en, eller använd en URL du fått av din lärare.

---

## Förutsättningar

- Python 3.12+
- Docker
- Ett konto på [KTH Cloud](https://app.cloud.cbh.kth.se)
- En driftsatt datalake (se [TUTORIAL-DUCKLAKE.md](TUTORIAL-DUCKLAKE.md))

---

## Arkitektur

```
<klient-deployment>        →HTTP→        <datalake-deployment>
(Python-klient)                          (FastAPI + DuckLake)
```

Exempel:
- Datalake: `https://misty-abnormally-educated.app.cloud.cbh.kth.se`
- Klient: `https://python-deployment.app.cloud.cbh.kth.se`

---

## Steg 1 — Projektstruktur

Lägg till en `klient/`-mapp i ditt repo:

```
<repo-namn>/
└── klient/
    ├── klient.py
    ├── requirements.txt
    └── Dockerfile
```

---

## Steg 2 — Python-klienten

`klient/klient.py` hämtar data från datalakens API och visar den i en webbsida:

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
    produkter = hamta("/api/produkter")
    rader = "".join(
        f"<tr><td>{p['id']}</td><td>{p['namn']}</td><td>{p['pris']} kr</td></tr>"
        for p in produkter
    )
    return f"""<!DOCTYPE html><html><body>
        <h1>Produkter från datalaken</h1>
        <table border='1'>
            <tr><th>ID</th><th>Namn</th><th>Pris</th></tr>
            {rader}
        </table>
    </body></html>"""
```

> Byt ut `/api/produkter` mot vilken endpoint du vill hämta data från — se alla endpoints i [TUTORIAL-DUCKLAKE.md](TUTORIAL-DUCKLAKE.md).

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

> `DATALAKE_URL` sätts som miljövariabel i KTH Cloud — hårdkoda inte URL:en i Dockerfile.

---

## Steg 3 — GitHub Actions

Lägg till `.github/workflows/docker-klient.yml`:

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

Pusha till `main` — imagen byggs automatiskt.

---

## Steg 4 — Driftsätt klienten på KTH Cloud

1. Gå till [app.cloud.cbh.kth.se](https://app.cloud.cbh.kth.se) → **New deployment**
2. Fyll i:
   - **Image:** `ghcr.io/<ditt-github-användarnamn>/<repo-namn>/klient:latest`
   - **Port:** `8001`
   - **Visibility:** Public
3. Lägg till miljövariabel:
   - `DATALAKE_URL` = `https://<datalake-deployment>.app.cloud.cbh.kth.se`
4. **Ingen persistent storage behövs** — klienten lagrar ingenting

Klienten är nu live på `https://<klient-deployment>.app.cloud.cbh.kth.se`.

---

## Skriva data (POST med API-nyckel)

POST och DELETE kräver `X-API-Key`-headern:

```python
import requests

DATALAKE_URL = "https://<datalake-deployment>.app.cloud.cbh.kth.se"
API_KEY = "ditt-hemliga-lösenord"

# Skapa ny produkt
svar = requests.post(
    f"{DATALAKE_URL}/api/produkter",
    json={"namn": "Skärm", "pris": 3499.0},
    headers={"X-API-Key": API_KEY}
)
print(svar.json())

# Radera produkt
svar = requests.delete(
    f"{DATALAKE_URL}/api/produkter/1",
    headers={"X-API-Key": API_KEY}
)
print(svar.json())
```

---

## Källkod

Fullständig källkod: [github.com/WildRelation/ducklake-platform](https://github.com/WildRelation/ducklake-platform)

Live klient: [python-deployment.app.cloud.cbh.kth.se](https://python-deployment.app.cloud.cbh.kth.se)
