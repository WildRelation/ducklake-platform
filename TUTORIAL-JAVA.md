# Tutorial: Anslut till en DuckLake Datalake med Java

## Introduktion

I denna tutorial ansluter vi till en färdig datalake som redan är driftsatt på **KTH Cloud**. Du behöver inte skriva eller förstå någon Python-kod — datalaken körs som en Docker-container och du ansluter till den via **HTTP** med Java.

### Hur fungerar det?

DuckLake-filerna (Parquet + katalog) ligger på en persistent disk i molnet. En FastAPI-server exponerar datan som ett REST API. Du ansluter till det API:et precis som du skulle ansluta till vilken annan webbtjänst som helst.

```
Din Java-app  →  HTTP  →  Datalake API  →  DuckLake-filer
```

---

## Förutsättningar

- Java 11 eller senare (HttpClient är inbyggt)
- Docker
- Ett konto på [KTH Cloud](https://app.cloud.cbh.kth.se)
- Ett GitHub-konto

---

## Arkitektur

```
<din-java-app>                       <datalake-deployment>
(Java-klient)          →HTTP→        (Datalake — FastAPI + DuckLake)
                                              ↓
                                      /app/data (persistent volym)
                                      ├── katalog.duckdb
                                      └── lake/main/
                                          ├── kunder/    ← Parquet
                                          ├── produkter/ ← Parquet
                                          └── ordrar/    ← Parquet
```

---

## Steg 1 — Driftsätt datalaken på KTH Cloud

Du behöver inte bygga datalaken själv — använd den färdiga Docker-imagen.

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
   - `API_KEY` = `<ditt-hemliga-lösenord>` ← **välj ett eget lösenord**
5. Spara — datalaken är nu live på `https://<deployment-namn>.app.cloud.cbh.kth.se`

> **Varför persistent storage?** DuckLake lagrar data som filer. Utan en persistent volym försvinner all data varje gång containern startas om.

Verifiera att allt fungerar genom att öppna `https://<deployment-namn>.app.cloud.cbh.kth.se/api/kunder` i webbläsaren — du ska se en JSON-lista med kunder.

Exempel på en live datalake: `https://misty-abnormally-educated.app.cloud.cbh.kth.se`

---

## Steg 2 — Tillgängliga endpoints

| Metod | Endpoint | Kräver API-nyckel | Beskrivning |
|-------|----------|-------------------|-------------|
| GET | `/api/kunder` | Nej | Hämta alla kunder |
| GET | `/api/produkter` | Nej | Hämta alla produkter |
| GET | `/api/ordrar` | Nej | Hämta alla ordrar |
| GET | `/api/kunder/sok?q=anna` | Nej | Sök kunder |
| GET | `/api/produkter/sok?min_pris=500&max_pris=2000` | Nej | Filtrera produkter |
| GET | `/api/ordrar/sok?fran=2025-01-01&till=2025-12-31` | Nej | Filtrera ordrar på datum |
| GET | `/api/kunder/{id}/ordrar` | Nej | En kunds alla ordrar |
| GET | `/api/produkter/{id}/ordrar` | Nej | Kunder som köpt en produkt |
| GET | `/api/statistik/intakter-per-kund` | Nej | Total intäkt per kund |
| GET | `/api/statistik/basta-produkter` | Nej | Bästsäljande produkter |
| GET | `/api/statistik/ordrar-per-dag` | Nej | Ordrar per dag |
| POST | `/api/kunder` | **Ja** | Skapa ny kund |
| POST | `/api/produkter` | **Ja** | Skapa ny produkt |
| POST | `/api/ordrar` | **Ja** | Skapa ny order |
| DELETE | `/api/kunder/{id}` | **Ja** | Radera kund |
| DELETE | `/api/produkter/{id}` | **Ja** | Radera produkt |

---

## Steg 3 — Java-klient

Skapa ett nytt Java-projekt. Inget extra bibliotek behövs — `HttpClient` är inbyggt sedan Java 11.

### Grundstruktur

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class DatalakeKlient {

    static final String BASE_URL = "https://<deployment-namn>.app.cloud.cbh.kth.se";
    static final String API_KEY  = "ditt-hemliga-lösenord";
    static final HttpClient client = HttpClient.newHttpClient();

    public static void main(String[] args) throws Exception {
        System.out.println(hamtaKunder());
    }

    static String hamta(String endpoint) throws Exception {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(BASE_URL + endpoint))
            .GET()
            .build();
        return client.send(request, HttpResponse.BodyHandlers.ofString()).body();
    }
}
```

---

## Steg 4 — Hämta data (GET)

GET-anrop kräver ingen API-nyckel.

```java
// Hämta alla kunder
String kunder = hamta("/api/kunder");
System.out.println(kunder);

// Hämta alla produkter
String produkter = hamta("/api/produkter");
System.out.println(produkter);

// Hämta alla ordrar
String ordrar = hamta("/api/ordrar");
System.out.println(ordrar);
```

---

## Steg 5 — Sök och filtrera (GET med parametrar)

```java
// Sök kunder på namn eller email
String sokKunder = hamta("/api/kunder/sok?q=anna");
System.out.println(sokKunder);

// Filtrera produkter på prisintervall
String billigaProdukter = hamta("/api/produkter/sok?min_pris=500&max_pris=2000");
System.out.println(billigaProdukter);

// Filtrera ordrar på datum
String ordrarDatum = hamta("/api/ordrar/sok?fran=2025-01-01&till=2025-12-31");
System.out.println(ordrarDatum);

// Hämta en kunds alla ordrar
String kundOrdrar = hamta("/api/kunder/1/ordrar");
System.out.println(kundOrdrar);
```

---

## Steg 6 — Statistik (GET)

```java
// Intäkter per kund
String intakter = hamta("/api/statistik/intakter-per-kund");
System.out.println(intakter);

// Bästsäljande produkter
String basta = hamta("/api/statistik/basta-produkter");
System.out.println(basta);

// Ordrar per dag
String perDag = hamta("/api/statistik/ordrar-per-dag");
System.out.println(perDag);
```

---

## Steg 7 — Skriva data (POST)

POST-anrop kräver `X-API-Key`-headern med lösenordet du satte i Steg 1.

```java
// Skapa ny kund
String json = "{\"namn\":\"Java Klient\",\"email\":\"java@example.com\",\"telefon\":\"070-0000000\"}";

HttpRequest postRequest = HttpRequest.newBuilder()
    .uri(URI.create(BASE_URL + "/api/kunder"))
    .header("Content-Type", "application/json")
    .header("X-API-Key", API_KEY)
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();

HttpResponse<String> svar = client.send(postRequest, HttpResponse.BodyHandlers.ofString());
System.out.println("Status: " + svar.statusCode());
System.out.println("Svar: " + svar.body());
```

```java
// Skapa ny produkt
String json = "{\"namn\":\"Skärm\",\"pris\":3499.0,\"lagersaldo\":10}";

HttpRequest postRequest = HttpRequest.newBuilder()
    .uri(URI.create(BASE_URL + "/api/produkter"))
    .header("Content-Type", "application/json")
    .header("X-API-Key", API_KEY)
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();

HttpResponse<String> svar = client.send(postRequest, HttpResponse.BodyHandlers.ofString());
System.out.println(svar.body());
```

```java
// Skapa ny order (kund_id=1, produkt_id=2, antal=3)
String json = "{\"kund_id\":1,\"produkt_id\":2,\"antal\":3}";

HttpRequest postRequest = HttpRequest.newBuilder()
    .uri(URI.create(BASE_URL + "/api/ordrar"))
    .header("Content-Type", "application/json")
    .header("X-API-Key", API_KEY)
    .POST(HttpRequest.BodyPublishers.ofString(json))
    .build();

HttpResponse<String> svar = client.send(postRequest, HttpResponse.BodyHandlers.ofString());
System.out.println(svar.body());
```

---

## Steg 8 — Radera data (DELETE)

DELETE-anrop kräver också `X-API-Key`.

```java
// Radera kund med id=5
HttpRequest deleteRequest = HttpRequest.newBuilder()
    .uri(URI.create(BASE_URL + "/api/kunder/5"))
    .header("X-API-Key", API_KEY)
    .DELETE()
    .build();

HttpResponse<String> svar = client.send(deleteRequest, HttpResponse.BodyHandlers.ofString());
System.out.println("Status: " + svar.statusCode());
System.out.println("Svar: " + svar.body());
```

---

## Steg 9 — Dockerisera Java-klienten (valfritt)

Om du vill deploya Java-klienten på KTH Cloud, skapa en `Dockerfile`:

```dockerfile
FROM eclipse-temurin:21-jre-slim
WORKDIR /app
COPY DatalakeKlient.jar .
ENV BASE_URL=https://<deployment-namn>.app.cloud.cbh.kth.se
EXPOSE 8080
CMD ["java", "-jar", "DatalakeKlient.jar"]
```

> För ett mer komplett Java-projekt med Spring Boot, se Javas dokumentation.

---

## Komplett exempel

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class DatalakeKlient {

    static final String BASE_URL = "https://misty-abnormally-educated.app.cloud.cbh.kth.se";
    static final String API_KEY  = "ditt-hemliga-lösenord";
    static final HttpClient client = HttpClient.newHttpClient();

    public static void main(String[] args) throws Exception {
        // Hämta data
        System.out.println("=== Kunder ===");
        System.out.println(hamta("/api/kunder"));

        System.out.println("=== Bästsäljande produkter ===");
        System.out.println(hamta("/api/statistik/basta-produkter"));

        // Skapa en ny kund
        System.out.println("=== Skapar ny kund ===");
        String nyKund = "{\"namn\":\"Java Klient\",\"email\":\"java@example.com\"}";
        System.out.println(skicka("POST", "/api/kunder", nyKund));
    }

    static String hamta(String endpoint) throws Exception {
        HttpRequest req = HttpRequest.newBuilder()
            .uri(URI.create(BASE_URL + endpoint))
            .GET()
            .build();
        return client.send(req, HttpResponse.BodyHandlers.ofString()).body();
    }

    static String skicka(String metod, String endpoint, String json) throws Exception {
        HttpRequest.Builder builder = HttpRequest.newBuilder()
            .uri(URI.create(BASE_URL + endpoint))
            .header("Content-Type", "application/json")
            .header("X-API-Key", API_KEY);

        HttpRequest req = switch (metod) {
            case "POST"   -> builder.POST(HttpRequest.BodyPublishers.ofString(json)).build();
            case "DELETE" -> builder.DELETE().build();
            default       -> throw new IllegalArgumentException("Okänd metod: " + metod);
        };

        HttpResponse<String> svar = client.send(req, HttpResponse.BodyHandlers.ofString());
        return "Status " + svar.statusCode() + ": " + svar.body();
    }
}
```

---

## Källkod och live-exempel

Källkod (datalaken): [github.com/WildRelation/ducklake-platform](https://github.com/WildRelation/ducklake-platform)

Live datalake API: [misty-abnormally-educated.app.cloud.cbh.kth.se](https://misty-abnormally-educated.app.cloud.cbh.kth.se)

API-dokumentation: [misty-abnormally-educated.app.cloud.cbh.kth.se/docs](https://misty-abnormally-educated.app.cloud.cbh.kth.se/docs)
