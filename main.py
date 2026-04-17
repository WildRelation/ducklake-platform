from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from database import get_conn, init_db

app = FastAPI(title="Butik API")

init_db()

NAV = '<a href="/">← Tillbaka</a>'
STYLE = """
<style>
  body { font-family: Arial, sans-serif; max-width: 900px; margin: 60px auto; background: #f0f4f8; color: #333; }
  h1 { color: #2c7a7b; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px;
          overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-top: 16px; }
  th { background: #2c7a7b; color: white; padding: 12px; text-align: left; }
  td { padding: 10px 12px; border-bottom: 1px solid #eee; }
  a { color: #2c7a7b; }
  .card { background: white; border-radius: 12px; padding: 30px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
  nav a { margin-right: 16px; font-weight: bold; }
</style>
"""


def page(title: str, body: str) -> str:
    return f"<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'><title>{title}</title>{STYLE}</head><body>{body}</body></html>"


@app.get("/", response_class=HTMLResponse)
async def index():
    return page("Butik", """
        <div class='card'>
            <h1>Välkommen till Butik-API</h1>
            <nav>
                <a href='/kunder'>Kunder</a>
                <a href='/produkter'>Produkter</a>
                <a href='/ordrar'>Ordrar</a>
                <a href='/docs'>API-dokumentation</a>
            </nav>
        </div>
    """)


@app.get("/kunder", response_class=HTMLResponse)
async def visa_kunder():
    con = get_conn()
    rows = con.execute("SELECT id, namn, email, telefon FROM kunder ORDER BY id").fetchall()
    con.close()
    rader = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in rows)
    return page("Kunder", f"<h1>Kunder</h1>{NAV}<table><tr><th>ID</th><th>Namn</th><th>E-post</th><th>Telefon</th></tr>{rader}</table>")


@app.get("/produkter", response_class=HTMLResponse)
async def visa_produkter():
    con = get_conn()
    rows = con.execute("SELECT id, namn, pris, lagersaldo FROM produkter ORDER BY id").fetchall()
    con.close()
    rader = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]:.2f} kr</td><td>{r[3]}</td></tr>" for r in rows)
    return page("Produkter", f"<h1>Produkter</h1>{NAV}<table><tr><th>ID</th><th>Namn</th><th>Pris</th><th>Lagersaldo</th></tr>{rader}</table>")


@app.get("/ordrar", response_class=HTMLResponse)
async def visa_ordrar():
    con = get_conn()
    rows = con.execute("""
        SELECT o.id, k.namn, p.namn, o.antal, o.skapad
        FROM ordrar o
        JOIN kunder k ON k.id = o.kund_id
        JOIN produkter p ON p.id = o.produkt_id
        ORDER BY o.id
    """).fetchall()
    con.close()
    rader = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{str(r[4])[:16]}</td></tr>" for r in rows)
    return page("Ordrar", f"<h1>Ordrar</h1>{NAV}<table><tr><th>ID</th><th>Kund</th><th>Produkt</th><th>Antal</th><th>Datum</th></tr>{rader}</table>")
