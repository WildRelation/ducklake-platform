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
  body { font-family: Arial, sans-serif; max-width: 960px; margin: 60px auto; background: #f0f4f8; color: #333; }
  h1 { color: #2c7a7b; }
  h2 { color: #4a5568; margin-top: 40px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
  h3 { color: #2c7a7b; margin-top: 24px; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px;
          overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-top: 12px; }
  th { background: #2c7a7b; color: white; padding: 12px; text-align: left; }
  td { padding: 10px 12px; border-bottom: 1px solid #eee; }
  .badge { background: #e53e3e; color: white; padding: 2px 10px; border-radius: 20px;
           font-size: 0.8rem; margin-left: 8px; }
  .badge-green { background: #2c7a7b; color: white; padding: 2px 10px; border-radius: 20px;
                 font-size: 0.8rem; margin-left: 8px; }
  .card { background: white; border-radius: 12px; padding: 24px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 16px; }
  .url { font-size: 0.85rem; color: #718096; }
  nav a { margin-right: 16px; font-weight: bold; color: #2c7a7b; text-decoration: none; }
  .highlight { background: #fffbeb; font-weight: bold; }
</style>
"""

NAV = """
<nav>
  <a href="/">Översikt</a>
  <a href="/statistik">Statistik</a>
  <a href="/sok">Sök</a>
</nav>
"""


def hamta(endpoint: str):
    svar = requests.get(f"{DATALAKE_URL}{endpoint}", timeout=5)
    svar.raise_for_status()
    return svar.json()


@app.get("/", response_class=HTMLResponse)
async def index():
    try:
        kunder    = hamta("/api/kunder")
        produkter = hamta("/api/produkter")
        ordrar    = hamta("/api/ordrar")

        kunder_rader = "".join(
            f"<tr><td>{k['id']}</td><td><a href='/kund/{k['id']}'>{k['namn']}</a></td><td>{k['email']}</td><td>{k['telefon'] or ''}</td></tr>"
            for k in kunder
        )
        produkt_rader = "".join(
            f"<tr><td>{p['id']}</td><td><a href='/produkt/{p['id']}'>{p['namn']}</a></td><td>{p['pris']} kr</td><td>{p['lagersaldo']}</td></tr>"
            for p in produkter
        )
        order_rader = "".join(
            f"<tr><td>{o['id']}</td><td>{o['kund']}</td><td>{o['produkt']}</td><td>{o['antal']}</td><td>{o['skapad'][:16]}</td></tr>"
            for o in ordrar
        )

        return f"""<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'>
        <title>Datalake Klient</title>{STYLE}</head><body>
        <div class='card'>
            <h1>Datalake Klient <span class='badge'>Python</span></h1>
            <p class='url'>Hämtar data från: <strong>{DATALAKE_URL}</strong></p>
            {NAV}
        </div>

        <h2>Kunder ({len(kunder)})</h2>
        <table><tr><th>ID</th><th>Namn</th><th>E-post</th><th>Telefon</th></tr>{kunder_rader}</table>

        <h2>Produkter ({len(produkter)})</h2>
        <table><tr><th>ID</th><th>Namn</th><th>Pris</th><th>Lagersaldo</th></tr>{produkt_rader}</table>

        <h2>Ordrar ({len(ordrar)})</h2>
        <table><tr><th>ID</th><th>Kund</th><th>Produkt</th><th>Antal</th><th>Datum</th></tr>{order_rader}</table>
        </body></html>"""

    except Exception as e:
        return f"<h1>Fel: kunde inte nå datalaken</h1><p>{e}</p>"


@app.get("/statistik", response_class=HTMLResponse)
async def statistik():
    try:
        intakter    = hamta("/api/statistik/intakter-per-kund")
        produkter   = hamta("/api/statistik/basta-produkter")
        per_dag     = hamta("/api/statistik/ordrar-per-dag")

        intakt_rader = "".join(
            f"<tr><td>{r['namn']}</td><td>{r['antal_ordrar']}</td><td>{r['total_intakt']:.2f} kr</td></tr>"
            for r in intakter
        )
        produkt_rader = "".join(
            f"<tr{'class=highlight' if i == 0 else ''}><td>{r['namn']}</td><td>{r['pris']} kr</td><td>{r['sålda_enheter']}</td><td>{r['total_intakt']:.2f} kr</td></tr>"
            for i, r in enumerate(produkter)
        )
        dag_rader = "".join(
            f"<tr><td>{r['dag']}</td><td>{r['antal_ordrar']}</td><td>{r['daglig_intakt']:.2f} kr</td></tr>"
            for r in per_dag
        )

        total = sum(r['total_intakt'] for r in intakter)

        return f"""<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'>
        <title>Statistik</title>{STYLE}</head><body>
        <div class='card'>
            <h1>Statistik <span class='badge-green'>Aggregeringar</span></h1>
            <p>Total intäkt: <strong>{total:.2f} kr</strong></p>
            {NAV}
        </div>

        <h2>Intäkter per kund</h2>
        <table><tr><th>Kund</th><th>Antal ordrar</th><th>Total intäkt</th></tr>{intakt_rader}</table>

        <h2>Bästa produkter</h2>
        <table><tr><th>Produkt</th><th>Pris</th><th>Sålda enheter</th><th>Total intäkt</th></tr>{produkt_rader}</table>

        <h2>Ordrar per dag</h2>
        <table><tr><th>Dag</th><th>Antal ordrar</th><th>Daglig intäkt</th></tr>{dag_rader}</table>
        </body></html>"""

    except Exception as e:
        return f"<h1>Fel: kunde inte nå datalaken</h1><p>{e}</p>"


@app.get("/kund/{kund_id}", response_class=HTMLResponse)
async def kund_detalj(kund_id: int):
    try:
        data = hamta(f"/api/kunder/{kund_id}/ordrar")
        kund = data["kund"]
        ordrar = data["ordrar"]

        order_rader = "".join(
            f"<tr><td>{o['order_id']}</td><td>{o['produkt']}</td><td>{o['pris']} kr</td><td>{o['antal']}</td><td>{o['delsumma']:.2f} kr</td><td>{o['skapad'][:16]}</td></tr>"
            for o in ordrar
        )

        return f"""<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'>
        <title>{kund['namn']}</title>{STYLE}</head><body>
        <div class='card'>
            <h1>{kund['namn']} <span class='badge-green'>Kund #{kund['id']}</span></h1>
            <p>{kund['email']}</p>
            <p>Total: <strong>{data['totalt']:.2f} kr</strong></p>
            {NAV}
        </div>
        <h2>Ordrar</h2>
        <table><tr><th>Order</th><th>Produkt</th><th>Pris</th><th>Antal</th><th>Delsumma</th><th>Datum</th></tr>{order_rader}</table>
        </body></html>"""

    except Exception as e:
        return f"<h1>Fel</h1><p>{e}</p>"


@app.get("/produkt/{produkt_id}", response_class=HTMLResponse)
async def produkt_detalj(produkt_id: int):
    try:
        data    = hamta(f"/api/produkter/{produkt_id}/ordrar")
        produkt = data["produkt"]
        ordrar  = data["ordrar"]

        order_rader = "".join(
            f"<tr><td>{o['order_id']}</td><td>{o['kund']}</td><td>{o['email']}</td><td>{o['antal']}</td><td>{o['skapad'][:16]}</td></tr>"
            for o in ordrar
        )

        return f"""<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'>
        <title>{produkt['namn']}</title>{STYLE}</head><body>
        <div class='card'>
            <h1>{produkt['namn']} <span class='badge-green'>Produkt #{produkt['id']}</span></h1>
            <p>Pris: <strong>{produkt['pris']} kr</strong></p>
            {NAV}
        </div>
        <h2>Kunder som köpt denna produkt</h2>
        <table><tr><th>Order</th><th>Kund</th><th>E-post</th><th>Antal</th><th>Datum</th></tr>{order_rader}</table>
        </body></html>"""

    except Exception as e:
        return f"<h1>Fel</h1><p>{e}</p>"


@app.get("/sok", response_class=HTMLResponse)
async def sok(q: str = "", min_pris: str = "", max_pris: str = "", fran: str = "", till: str = ""):
    try:
        kunder_url    = f"/api/kunder/sok?q={q}"
        produkter_url = f"/api/produkter/sok?q={q}"
        if min_pris:
            produkter_url += f"&min_pris={min_pris}"
        if max_pris:
            produkter_url += f"&max_pris={max_pris}"
        ordrar_url = f"/api/ordrar/sok?fran={fran}&till={till}"

        kunder    = hamta(kunder_url)
        produkter = hamta(produkter_url)
        ordrar    = hamta(ordrar_url)

        kunder_rader = "".join(
            f"<tr><td>{k['id']}</td><td><a href='/kund/{k['id']}'>{k['namn']}</a></td><td>{k['email']}</td></tr>"
            for k in kunder
        ) or "<tr><td colspan='3'>Inga resultat</td></tr>"

        produkt_rader = "".join(
            f"<tr><td>{p['id']}</td><td><a href='/produkt/{p['id']}'>{p['namn']}</a></td><td>{p['pris']} kr</td><td>{p['lagersaldo']}</td></tr>"
            for p in produkter
        ) or "<tr><td colspan='4'>Inga resultat</td></tr>"

        order_rader = "".join(
            f"<tr><td>{o['id']}</td><td>{o['kund']}</td><td>{o['produkt']}</td><td>{o['antal']}</td><td>{o['skapad'][:16]}</td></tr>"
            for o in ordrar
        ) or "<tr><td colspan='5'>Inga resultat</td></tr>"

        return f"""<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'>
        <title>Sök</title>{STYLE}</head><body>
        <div class='card'>
            <h1>Sök <span class='badge-green'>Filtrering</span></h1>
            {NAV}
            <form method='get' action='/sok' style='display:flex;gap:12px;flex-wrap:wrap;margin-top:16px;align-items:flex-end;'>
                <div><label style='display:block;font-size:0.85rem;color:#555'>Sökord</label>
                     <input name='q' value='{q}' placeholder='namn, email...' style='padding:8px;border:1px solid #ccc;border-radius:6px'></div>
                <div><label style='display:block;font-size:0.85rem;color:#555'>Min pris</label>
                     <input name='min_pris' value='{min_pris}' type='number' placeholder='0' style='width:90px;padding:8px;border:1px solid #ccc;border-radius:6px'></div>
                <div><label style='display:block;font-size:0.85rem;color:#555'>Max pris</label>
                     <input name='max_pris' value='{max_pris}' type='number' placeholder='9999' style='width:90px;padding:8px;border:1px solid #ccc;border-radius:6px'></div>
                <div><label style='display:block;font-size:0.85rem;color:#555'>Ordrar från</label>
                     <input name='fran' value='{fran}' type='date' style='padding:8px;border:1px solid #ccc;border-radius:6px'></div>
                <div><label style='display:block;font-size:0.85rem;color:#555'>Ordrar till</label>
                     <input name='till' value='{till}' type='date' style='padding:8px;border:1px solid #ccc;border-radius:6px'></div>
                <button type='submit' style='padding:8px 16px;background:#2c7a7b;color:white;border:none;border-radius:6px;cursor:pointer'>Sök</button>
            </form>
        </div>

        <h2>Kunder ({len(kunder)})</h2>
        <table><tr><th>ID</th><th>Namn</th><th>E-post</th></tr>{kunder_rader}</table>

        <h2>Produkter ({len(produkter)})</h2>
        <table><tr><th>ID</th><th>Namn</th><th>Pris</th><th>Lagersaldo</th></tr>{produkt_rader}</table>

        <h2>Ordrar ({len(ordrar)})</h2>
        <table><tr><th>ID</th><th>Kund</th><th>Produkt</th><th>Antal</th><th>Datum</th></tr>{order_rader}</table>
        </body></html>"""

    except Exception as e:
        return f"<h1>Fel: kunde inte nå datalaken</h1><p>{e}</p>"
