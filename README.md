# DuckLake Dataset Platform

En molndriftsatt datalake-plattform byggd med **DuckLake**, **FastAPI**, **Python** och **Spring Boot (Java)**. Driftsatt på **KTH Cloud**.

---

## Arkitektur

```
ducklake-datasets                python-deployment
(Spring Boot — Java)   →HTTP→   (FastAPI — Python klient)
         ↓                                ↓
         └──────────────┬─────────────────┘
                        ↓
          misty-abnormally-educated
          (FastAPI + DuckLake — REST API)
                        ↓
              /app/data (persistent volym)
              ├── katalog.duckdb
              └── lake/main/
                  ├── kunder/         ← Parquet
                  ├── produkter/      ← Parquet
                  ├── ordrar/         ← Parquet
                  ├── vader_stockholm/← Parquet
                  └── befolkning_sverige/ ← Parquet
```

---

## Deployments på KTH Cloud

| Deployment | Teknologi | Port | Beskrivning |
|------------|-----------|------|-------------|
| `misty-abnormally-educated` | FastAPI + DuckLake | 8000 | Datalake REST API |
| `python-deployment` | FastAPI (Python) | 8001 | Python-klient |
| `ducklake-datasets` | Spring Boot (Java) | 8080 | Kaggle-liknande sajt |

---

## Teknikstack

| Komponent | Teknologi |
|-----------|-----------|
| Datalake | DuckLake (DuckDB + Parquet) |
| REST API | FastAPI (Python) |
| Python-klient | FastAPI + requests |
| Java-sajt | Spring Boot + Thymeleaf |
| Container | Docker |
| CI/CD | GitHub Actions → GHCR |
| Hosting | KTH Cloud (Kubernetes + Nginx) |
| Lagring | Persistent volume (`ducklake-data`) |

---

## Projektstruktur

```
butik-api/
├── main.py              # FastAPI REST API + HTML-sidor
├── database.py          # DuckLake-anslutning
├── requirements.txt     # Python-beroenden
├── Dockerfile           # Container för datalaken
├── klient/
│   ├── klient.py        # Python-klient (FastAPI)
│   ├── requirements.txt
│   └── Dockerfile
├── kaggle/
│   ├── pom.xml          # Maven-konfiguration
│   ├── Dockerfile
│   └── src/main/
│       ├── java/se/kth/datalake/
│       │   ├── DatalakeApp.java
│       │   ├── controller/DatasetController.java
│       │   ├── service/DatalakeService.java
│       │   └── model/Dataset.java, DatasetDetalj.java
│       └── resources/
│           ├── application.properties
│           └── templates/
│               ├── index.html   # Startsida med dataset-kort
│               ├── dataset.html # Dataset-detaljsida
│               └── upload.html  # Uppladdningssida
├── .github/workflows/
│   ├── docker.yml           # Bygger datalake-imagen
│   ├── docker-klient.yml    # Bygger Python-klient-imagen
│   └── docker-kaggle.yml    # Bygger Spring Boot-imagen
├── TUTORIAL-PYTHON.md   # Tutorial för Python-studenter
├── TUTORIAL-JAVA.md     # Tutorial för Java-studenter
└── archive/             # Oanvända filer
```

---

## API-endpoints

### Grundläggande CRUD

| Metod | Endpoint | Auth | Beskrivning |
|-------|----------|------|-------------|
| GET | `/api/kunder` | Nej | Hämta alla kunder |
| GET | `/api/produkter` | Nej | Hämta alla produkter |
| GET | `/api/ordrar` | Nej | Hämta alla ordrar |
| POST | `/api/kunder` | **Ja** | Skapa ny kund |
| POST | `/api/produkter` | **Ja** | Skapa ny produkt |
| POST | `/api/ordrar` | **Ja** | Skapa ny order |
| DELETE | `/api/kunder/{id}` | **Ja** | Radera kund |
| DELETE | `/api/produkter/{id}` | **Ja** | Radera produkt |

### Filtrering

| Metod | Endpoint | Beskrivning |
|-------|----------|-------------|
| GET | `/api/kunder/sok?q=anna` | Sök kunder på namn/email |
| GET | `/api/produkter/sok?min_pris=500&max_pris=2000` | Filtrera produkter |
| GET | `/api/ordrar/sok?fran=2025-01-01&till=2025-12-31` | Filtrera ordrar på datum |

### Aggregeringar

| Metod | Endpoint | Beskrivning |
|-------|----------|-------------|
| GET | `/api/statistik/intakter-per-kund` | Total intäkt per kund |
| GET | `/api/statistik/basta-produkter` | Produkter rankade efter försäljning |
| GET | `/api/statistik/ordrar-per-dag` | Ordrar och intäkt per dag |

### Joins

| Metod | Endpoint | Beskrivning |
|-------|----------|-------------|
| GET | `/api/kunder/{id}/ordrar` | En kunds alla ordrar med totalsumma |
| GET | `/api/produkter/{id}/ordrar` | Kunder som köpt en produkt |

### Datasets

| Metod | Endpoint | Auth | Beskrivning |
|-------|----------|------|-------------|
| GET | `/api/datasets` | Nej | Lista alla datasets |
| GET | `/api/datasets/{namn}` | Nej | Hämta data från ett dataset |
| POST | `/api/datasets/upload` | **Ja** | Ladda upp CSV/Parquet som ny tabell |

---

## Autentisering

Skrivoperationer (POST/DELETE och uppladdning) kräver headern `X-API-Key`:

```http
X-API-Key: ditt-hemliga-lösenord
```

Lösenordet sätts som miljövariabeln `API_KEY` i KTH Cloud — aldrig hårdkodat i koden.

---

## Inbyggda datasets

| Dataset | Beskrivning | Rader |
|---------|-------------|-------|
| `kunder` | Kundregister | 20 |
| `produkter` | Produktkatalog | 15 |
| `ordrar` | Orderhistorik | 48 |
| `vader_stockholm` | Väderdata Stockholm 2024 | 24 |
| `befolkning_sverige` | Svenska städer med befolkningsdata | 20 |

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

## Köra lokalt

```bash
# Datalaken
source venv/bin/activate
export CATALOG_PATH=./data/katalog.duckdb
export DATA_PATH=./data/lake/
export API_KEY=hemlig
uvicorn main:app --reload

# Python-klienten
export DATALAKE_URL=http://localhost:8000
cd klient && uvicorn klient:app --port 8001 --reload
```

---

## CI/CD

Varje push till `main` triggar GitHub Actions som bygger och pushar Docker-images till GHCR:

| Image | Triggas av |
|-------|------------|
| `ghcr.io/wildrelation/butik-api:latest` | Alla pushes |
| `ghcr.io/wildrelation/butik-api/klient:latest` | Ändringar i `klient/` |
| `ghcr.io/wildrelation/butik-api/kaggle:latest` | Ändringar i `kaggle/` |

---

## Live

| Tjänst | URL |
|--------|-----|
| Datalake API | https://misty-abnormally-educated.app.cloud.cbh.kth.se |
| API-dokumentation | https://misty-abnormally-educated.app.cloud.cbh.kth.se/docs |
| Python-klient | https://python-deployment.app.cloud.cbh.kth.se |
| Dataset-sajt (Java) | https://ducklake-datasets.app.cloud.cbh.kth.se |

---

## Tutorials

- [TUTORIAL-PYTHON.md](TUTORIAL-PYTHON.md) — Bygg allt från grunden med Python
- [TUTORIAL-JAVA.md](TUTORIAL-JAVA.md) — Anslut till datalaken med Java
