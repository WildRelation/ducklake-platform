import requests
import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

DATALAKE_URL = os.getenv(
    "DATALAKE_URL",
    "https://misty-abnormally-educated.app.cloud.cbh.kth.se"
)

app = FastAPI(title="Datalake Klient")

STYLE = """
<style>
  body { font-family: Arial, sans-serif; max-width: 900px; margin: 60px auto; background: #f0f4f8; }
  h1 { color: #2c7a7b; }
  h2 { color: #4a5568; margin-top: 32px; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px;
          overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-top: 12px; }
  th { background: #2c7a7b; color: white; padding: 12px; text-align: left; }
  td { padding: 10px 12px; border-bottom: 1px solid #eee; }
  .badge { background: #e53e3e; color: white; padding: 2px 10px; border-radius: 20px;
           font-size: 0.8rem; margin-left: 8px; }
  .card { background: white; border-radius: 12px; padding: 24px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 12px; }
  .url { font-size: 0.85rem; color: #718096; }
</style>
"""


def hamta(endpoint: str):
    svar = requests.get(f"{DATALAKE_URL}{endpoint}", timeout=5)
    svar.raise_for_status()
    return svar.json()


@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        kunder   = hamta("/api/kunder")
        produkter = hamta("/api/produkter")
        ordrar   = hamta("/api/ordrar")

        kunder_rader = "".join(
            f"<tr><td>{k['id']}</td><td>{k['namn']}</td><td>{k['email']}</td><td>{k['telefon'] or ''}</td></tr>"
            for k in kunder
        )
        produkt_rader = "".join(
            f"<tr><td>{p['id']}</td><td>{p['namn']}</td><td>{p['pris']} kr</td><td>{p['lagersaldo']}</td></tr>"
            for p in produkter
        )
        order_rader = "".join(
            f"<tr><td>{o['id']}</td><td>{o['kund']}</td><td>{o['produkt']}</td><td>{o['antal']}</td></tr>"
            for o in ordrar
        )

        return f"""<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'>
        <title>Datalake Klient</title>{STYLE}</head><body>
        <div class='card'>
            <h1>Datalake Klient <span class='badge'>Python</span></h1>
            <p class='url'>Hämtar data från: <strong>{DATALAKE_URL}</strong></p>
        </div>

        <h2>Kunder ({len(kunder)})</h2>
        <table><tr><th>ID</th><th>Namn</th><th>E-post</th><th>Telefon</th></tr>{kunder_rader}</table>

        <h2>Produkter ({len(produkter)})</h2>
        <table><tr><th>ID</th><th>Namn</th><th>Pris</th><th>Lagersaldo</th></tr>{produkt_rader}</table>

        <h2>Ordrar ({len(ordrar)})</h2>
        <table><tr><th>ID</th><th>Kund</th><th>Produkt</th><th>Antal</th></tr>{order_rader}</table>
        </body></html>"""

    except Exception as e:
        return f"<h1>Fel: kunde inte nå datalaken</h1><p>{e}</p>"
