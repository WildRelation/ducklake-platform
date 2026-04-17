from fastapi import FastAPI, Form, Header, HTTPException, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from database import get_conn, init_db
from pydantic import BaseModel
from typing import Optional
import os
import secrets
import tempfile

API_KEY = os.getenv("API_KEY", "change-me")


def kontrollera_nyckel(x_api_key: str = Header(...)):
    if not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Ogiltig API-nyckel")

app = FastAPI(title="Butik API")

init_db()

# Seed om databasen är tom
_con = get_conn()
if _con.execute("SELECT COUNT(*) FROM butik.kunder").fetchone()[0] == 0:
    _con.executemany("INSERT INTO butik.kunder VALUES (?, ?, ?, ?)", [
        (1, "Anna Svensson",   "anna@example.com",  "070-1234567"),
        (2, "Erik Johansson",  "erik@example.com",  "073-9876543"),
        (3, "Maria Lindqvist", "maria@example.com", "076-5551234"),
    ])
    _con.executemany("INSERT INTO butik.produkter VALUES (?, ?, ?, ?)", [
        (1, "Laptop",      9999.0, 15),
        (2, "Hörlurar",     799.0, 50),
        (3, "Tangentbord", 1299.0, 30),
        (4, "Mus",          399.0, 80),
    ])
    _con.executemany("INSERT INTO butik.ordrar (id, kund_id, produkt_id, antal) VALUES (?, ?, ?, ?)", [
        (1, 1, 1, 1), (2, 1, 2, 2), (3, 2, 3, 1), (4, 3, 4, 3),
    ])
_con.close()

NAV = '<a href="/">← Tillbaka</a>'
STYLE = """
<style>
  body { font-family: Arial, sans-serif; max-width: 960px; margin: 60px auto; background: #f0f4f8; color: #333; }
  h1, h2 { color: #2c7a7b; }
  table { width: 100%; border-collapse: collapse; background: white; border-radius: 12px;
          overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-top: 16px; }
  th { background: #2c7a7b; color: white; padding: 12px; text-align: left; }
  td { padding: 10px 12px; border-bottom: 1px solid #eee; }
  a { color: #2c7a7b; }
  .card { background: white; border-radius: 12px; padding: 30px;
          box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 24px; }
  nav a { margin-right: 16px; font-weight: bold; }
  .badge { background: #2c7a7b; color: white; padding: 2px 10px; border-radius: 20px;
           font-size: 0.8rem; margin-left: 8px; vertical-align: middle; }
  form { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; align-items: flex-end; }
  input, select { padding: 8px 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 0.95rem; }
  label { font-size: 0.85rem; color: #555; display: block; margin-bottom: 2px; }
  .btn     { padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 0.95rem; }
  .btn-add { background: #2c7a7b; color: white; }
  .btn-del { background: #e53e3e; color: white; padding: 4px 10px; font-size: 0.85rem; }
</style>
"""


def page(title: str, body: str) -> str:
    return f"<!DOCTYPE html><html lang='sv'><head><meta charset='UTF-8'><title>{title}</title>{STYLE}</head><body>{body}</body></html>"


def redirect(url: str):
    return RedirectResponse(url=url, status_code=303)


@app.get("/", response_class=HTMLResponse)
async def index():
    return page("Butik", """
        <div class='card'>
            <h1>Välkommen till Butik-API <span class='badge'>DuckLake</span></h1>
            <nav>
                <a href='/kunder'>Kunder</a>
                <a href='/produkter'>Produkter</a>
                <a href='/ordrar'>Ordrar</a>
                <a href='/snapshots'>Snapshots</a>
                <a href='/docs'>API-dokumentation</a>
            </nav>
        </div>
    """)


# ── KUNDER ────────────────────────────────────────────────────────────────────

@app.get("/kunder", response_class=HTMLResponse)
async def visa_kunder(fel: str = ""):
    con = get_conn()
    rows = con.execute("SELECT id, namn, email, telefon FROM butik.kunder ORDER BY id").fetchall()
    con.close()
    rader = "".join(f"""
        <tr>
            <td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3] or ''}</td>
            <td>
                <form method='post' action='/kunder/{r[0]}/radera' style='display:inline'>
                    <input type='password' name='lösenord' placeholder='Lösenord' style='width:100px;padding:4px;border:1px solid #ccc;border-radius:4px'>
                    <button class='btn btn-del'>Ta bort</button>
                </form>
            </td>
        </tr>""" for r in rows)
    felmeddelande = "<p style='color:red'>Fel lösenord!</p>" if fel else ""
    return page("Kunder", f"""
        <h1>Kunder <span class='badge'>DuckLake</span></h1>{NAV}
        {felmeddelande}
        <div class='card'>
            <h2>Lägg till kund</h2>
            <form method='post' action='/kunder/ny'>
                <div><label>Namn</label><input name='namn' required></div>
                <div><label>E-post</label><input name='email' type='email' required></div>
                <div><label>Telefon</label><input name='telefon'></div>
                <div><label>Lösenord</label><input name='lösenord' type='password' required></div>
                <button class='btn btn-add'>Lägg till</button>
            </form>
        </div>
        <table>
            <tr><th>ID</th><th>Namn</th><th>E-post</th><th>Telefon</th><th></th></tr>
            {rader}
        </table>
    """)


@app.post("/kunder/ny")
async def ny_kund(namn: str = Form(...), email: str = Form(...), telefon: str = Form(""), lösenord: str = Form("")):
    if not secrets.compare_digest(lösenord.encode(), API_KEY.encode()):
        return RedirectResponse(url="/kunder?fel=fel-lösenord", status_code=303)
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.kunder").fetchone()[0]
    con.execute("INSERT INTO butik.kunder VALUES (?, ?, ?, ?)", [nid, namn, email, telefon or None])
    con.close()
    return redirect("/kunder")


@app.post("/kunder/{kund_id}/radera")
async def radera_kund(kund_id: int, lösenord: str = Form("")):
    if not secrets.compare_digest(lösenord.encode(), API_KEY.encode()):
        return RedirectResponse(url="/kunder?fel=fel-lösenord", status_code=303)
    con = get_conn()
    con.execute("DELETE FROM butik.ordrar WHERE kund_id = ?", [kund_id])
    con.execute("DELETE FROM butik.kunder WHERE id = ?", [kund_id])
    con.close()
    return redirect("/kunder")


# ── PRODUKTER ─────────────────────────────────────────────────────────────────

@app.get("/produkter", response_class=HTMLResponse)
async def visa_produkter(fel: str = ""):
    con = get_conn()
    rows = con.execute("SELECT id, namn, pris, lagersaldo FROM butik.produkter ORDER BY id").fetchall()
    con.close()
    rader = "".join(f"""
        <tr>
            <td>{r[0]}</td><td>{r[1]}</td><td>{r[2]:.2f} kr</td><td>{r[3]}</td>
            <td>
                <form method='post' action='/produkter/{r[0]}/radera' style='display:inline'>
                    <input type='password' name='lösenord' placeholder='Lösenord' style='width:100px;padding:4px;border:1px solid #ccc;border-radius:4px'>
                    <button class='btn btn-del'>Ta bort</button>
                </form>
            </td>
        </tr>""" for r in rows)
    felmeddelande = "<p style='color:red'>Fel lösenord!</p>" if fel else ""
    return page("Produkter", f"""
        <h1>Produkter <span class='badge'>DuckLake</span></h1>{NAV}
        {felmeddelande}
        <div class='card'>
            <h2>Lägg till produkt</h2>
            <form method='post' action='/produkter/ny'>
                <div><label>Namn</label><input name='namn' required></div>
                <div><label>Pris (kr)</label><input name='pris' type='number' step='0.01' required></div>
                <div><label>Lagersaldo</label><input name='lagersaldo' type='number' value='0'></div>
                <div><label>Lösenord</label><input name='lösenord' type='password' required></div>
                <button class='btn btn-add'>Lägg till</button>
            </form>
        </div>
        <table>
            <tr><th>ID</th><th>Namn</th><th>Pris</th><th>Lagersaldo</th><th></th></tr>
            {rader}
        </table>
    """)


@app.post("/produkter/ny")
async def ny_produkt(namn: str = Form(...), pris: float = Form(...), lagersaldo: int = Form(0), lösenord: str = Form("")):
    if not secrets.compare_digest(lösenord.encode(), API_KEY.encode()):
        return RedirectResponse(url="/produkter?fel=fel-lösenord", status_code=303)
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.produkter").fetchone()[0]
    con.execute("INSERT INTO butik.produkter VALUES (?, ?, ?, ?)", [nid, namn, pris, lagersaldo])
    con.close()
    return redirect("/produkter")


@app.post("/produkter/{produkt_id}/radera")
async def radera_produkt(produkt_id: int, lösenord: str = Form("")):
    if not secrets.compare_digest(lösenord.encode(), API_KEY.encode()):
        return RedirectResponse(url="/produkter?fel=fel-lösenord", status_code=303)
    con = get_conn()
    con.execute("DELETE FROM butik.ordrar WHERE produkt_id = ?", [produkt_id])
    con.execute("DELETE FROM butik.produkter WHERE id = ?", [produkt_id])
    con.close()
    return redirect("/produkter")


# ── ORDRAR ────────────────────────────────────────────────────────────────────

@app.get("/ordrar", response_class=HTMLResponse)
async def visa_ordrar(fel: str = ""):
    con = get_conn()
    rows = con.execute("""
        SELECT o.id, k.namn, p.namn, o.antal, o.skapad
        FROM butik.ordrar o
        JOIN butik.kunder k    ON k.id = o.kund_id
        JOIN butik.produkter p ON p.id = o.produkt_id
        ORDER BY o.id
    """).fetchall()
    kunder   = con.execute("SELECT id, namn FROM butik.kunder ORDER BY namn").fetchall()
    produkter = con.execute("SELECT id, namn FROM butik.produkter ORDER BY namn").fetchall()
    con.close()

    rader = "".join(f"""
        <tr>
            <td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{str(r[4])[:16]}</td>
            <td>
                <form method='post' action='/ordrar/{r[0]}/radera' style='display:inline'>
                    <input type='password' name='lösenord' placeholder='Lösenord' style='width:100px;padding:4px;border:1px solid #ccc;border-radius:4px'>
                    <button class='btn btn-del'>Ta bort</button>
                </form>
            </td>
        </tr>""" for r in rows)

    kund_options    = "".join(f"<option value='{k[0]}'>{k[1]}</option>" for k in kunder)
    produkt_options = "".join(f"<option value='{p[0]}'>{p[1]}</option>" for p in produkter)
    felmeddelande   = "<p style='color:red'>Fel lösenord!</p>" if fel else ""

    return page("Ordrar", f"""
        <h1>Ordrar <span class='badge'>DuckLake</span></h1>{NAV}
        {felmeddelande}
        <div class='card'>
            <h2>Lägg till order</h2>
            <form method='post' action='/ordrar/ny'>
                <div><label>Kund</label><select name='kund_id'>{kund_options}</select></div>
                <div><label>Produkt</label><select name='produkt_id'>{produkt_options}</select></div>
                <div><label>Antal</label><input name='antal' type='number' value='1' min='1' required></div>
                <div><label>Lösenord</label><input name='lösenord' type='password' required></div>
                <button class='btn btn-add'>Lägg till</button>
            </form>
        </div>
        <table>
            <tr><th>ID</th><th>Kund</th><th>Produkt</th><th>Antal</th><th>Datum</th><th></th></tr>
            {rader}
        </table>
    """)


@app.post("/ordrar/ny")
async def ny_order(kund_id: int = Form(...), produkt_id: int = Form(...), antal: int = Form(...), lösenord: str = Form("")):
    if not secrets.compare_digest(lösenord.encode(), API_KEY.encode()):
        return RedirectResponse(url="/ordrar?fel=fel-lösenord", status_code=303)
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.ordrar").fetchone()[0]
    con.execute("INSERT INTO butik.ordrar (id, kund_id, produkt_id, antal) VALUES (?, ?, ?, ?)",
                [nid, kund_id, produkt_id, antal])
    con.close()
    return redirect("/ordrar")


@app.post("/ordrar/{order_id}/radera")
async def radera_order(order_id: int, lösenord: str = Form("")):
    if not secrets.compare_digest(lösenord.encode(), API_KEY.encode()):
        return RedirectResponse(url="/ordrar?fel=fel-lösenord", status_code=303)
    con = get_conn()
    con.execute("DELETE FROM butik.ordrar WHERE id = ?", [order_id])
    con.close()
    return redirect("/ordrar")


# ── SNAPSHOTS ─────────────────────────────────────────────────────────────────

@app.get("/snapshots", response_class=HTMLResponse)
async def visa_snapshots():
    con = get_conn()
    rows = con.execute("""
        SELECT snapshot_id, snapshot_time, schema_version, changes
        FROM ducklake_snapshots('butik')
        ORDER BY snapshot_id DESC
        LIMIT 50
    """).fetchall()
    con.close()
    rader = "".join(
        f"<tr><td>{r[0]}</td><td>{str(r[1])[:19]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>"
        for r in rows
    )
    return page("Snapshots", f"""
        <h1>Snapshots <span class='badge'>Time Travel</span></h1>{NAV}
        <p>Varje skrivoperation skapar en ny snapshot — historiken bevaras.</p>
        <table>
            <tr><th>Snapshot ID</th><th>Tidpunkt</th><th>Schema-version</th><th>Ändringar</th></tr>
            {rader}
        </table>
    """)


# ── JSON API ──────────────────────────────────────────────────────────────────

class NyKund(BaseModel):
    namn: str
    email: str
    telefon: Optional[str] = None

class NyProdukt(BaseModel):
    namn: str
    pris: float
    lagersaldo: Optional[int] = 0

class NyOrder(BaseModel):
    kund_id: int
    produkt_id: int
    antal: int


@app.get("/api/kunder")
async def api_kunder():
    con = get_conn()
    rows = con.execute("SELECT id, namn, email, telefon FROM butik.kunder ORDER BY id").fetchall()
    con.close()
    return [{"id": r[0], "namn": r[1], "email": r[2], "telefon": r[3]} for r in rows]


@app.get("/api/produkter")
async def api_produkter():
    con = get_conn()
    rows = con.execute("SELECT id, namn, pris, lagersaldo FROM butik.produkter ORDER BY id").fetchall()
    con.close()
    return [{"id": r[0], "namn": r[1], "pris": r[2], "lagersaldo": r[3]} for r in rows]


@app.get("/api/ordrar")
async def api_ordrar():
    con = get_conn()
    rows = con.execute("""
        SELECT o.id, k.namn, p.namn, o.antal, o.skapad
        FROM butik.ordrar o
        JOIN butik.kunder k    ON k.id = o.kund_id
        JOIN butik.produkter p ON p.id = o.produkt_id
        ORDER BY o.id
    """).fetchall()
    con.close()
    return [{"id": r[0], "kund": r[1], "produkt": r[2], "antal": r[3], "skapad": str(r[4])} for r in rows]


@app.post("/api/kunder", status_code=201, dependencies=[Depends(kontrollera_nyckel)])
async def api_ny_kund(kund: NyKund):
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.kunder").fetchone()[0]
    con.execute("INSERT INTO butik.kunder VALUES (?, ?, ?, ?)", [nid, kund.namn, kund.email, kund.telefon])
    con.close()
    return {"id": nid, "namn": kund.namn, "email": kund.email, "telefon": kund.telefon}


@app.post("/api/produkter", status_code=201, dependencies=[Depends(kontrollera_nyckel)])
async def api_ny_produkt(produkt: NyProdukt):
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.produkter").fetchone()[0]
    con.execute("INSERT INTO butik.produkter VALUES (?, ?, ?, ?)", [nid, produkt.namn, produkt.pris, produkt.lagersaldo])
    con.close()
    return {"id": nid, "namn": produkt.namn, "pris": produkt.pris, "lagersaldo": produkt.lagersaldo}


@app.post("/api/ordrar", status_code=201, dependencies=[Depends(kontrollera_nyckel)])
async def api_ny_order(order: NyOrder):
    con = get_conn()
    nid = con.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM butik.ordrar").fetchone()[0]
    con.execute("INSERT INTO butik.ordrar (id, kund_id, produkt_id, antal) VALUES (?, ?, ?, ?)",
                [nid, order.kund_id, order.produkt_id, order.antal])
    con.close()
    return {"id": nid, "kund_id": order.kund_id, "produkt_id": order.produkt_id, "antal": order.antal}


@app.delete("/api/kunder/{kund_id}", dependencies=[Depends(kontrollera_nyckel)])
async def api_radera_kund(kund_id: int):
    con = get_conn()
    con.execute("DELETE FROM butik.ordrar WHERE kund_id = ?", [kund_id])
    con.execute("DELETE FROM butik.kunder WHERE id = ?", [kund_id])
    con.close()
    return {"deleted": kund_id}

@app.get("/healthz")
async def health():
    return {"status": "ok"}

@app.delete("/api/produkter/{produkt_id}", dependencies=[Depends(kontrollera_nyckel)])
async def api_radera_produkt(produkt_id: int):
    con = get_conn()
    con.execute("DELETE FROM butik.ordrar WHERE produkt_id = ?", [produkt_id])
    con.execute("DELETE FROM butik.produkter WHERE id = ?", [produkt_id])
    con.close()
    return {"deleted": produkt_id}


# ── FILTRERING ────────────────────────────────────────────────────────────────

@app.get("/api/kunder/sok")
async def sok_kunder(q: str = ""):
    con = get_conn()
    rows = con.execute(
        "SELECT id, namn, email, telefon FROM butik.kunder WHERE namn ILIKE ? OR email ILIKE ? ORDER BY id",
        [f"%{q}%", f"%{q}%"]
    ).fetchall()
    con.close()
    return [{"id": r[0], "namn": r[1], "email": r[2], "telefon": r[3]} for r in rows]


@app.get("/api/produkter/sok")
async def sok_produkter(q: str = "", min_pris: float = 0, max_pris: float = 9999999, min_lager: int = 0):
    con = get_conn()
    rows = con.execute(
        """SELECT id, namn, pris, lagersaldo FROM butik.produkter
           WHERE namn ILIKE ?
             AND pris BETWEEN ? AND ?
             AND lagersaldo >= ?
           ORDER BY pris""",
        [f"%{q}%", min_pris, max_pris, min_lager]
    ).fetchall()
    con.close()
    return [{"id": r[0], "namn": r[1], "pris": r[2], "lagersaldo": r[3]} for r in rows]


@app.get("/api/ordrar/sok")
async def sok_ordrar(fran: str = "", till: str = ""):
    con = get_conn()
    query = """
        SELECT o.id, k.namn, p.namn, o.antal, o.skapad
        FROM butik.ordrar o
        JOIN butik.kunder k    ON k.id = o.kund_id
        JOIN butik.produkter p ON p.id = o.produkt_id
        WHERE (? = '' OR o.skapad >= ?::TIMESTAMP)
          AND (? = '' OR o.skapad <= ?::TIMESTAMP)
        ORDER BY o.skapad DESC
    """
    rows = con.execute(query, [fran, fran, till, till]).fetchall()
    con.close()
    return [{"id": r[0], "kund": r[1], "produkt": r[2], "antal": r[3], "skapad": str(r[4])} for r in rows]


# ── AGGREGERINGAR ─────────────────────────────────────────────────────────────

@app.get("/api/statistik/intakter-per-kund")
async def intakter_per_kund():
    con = get_conn()
    rows = con.execute("""
        SELECT k.id, k.namn, COUNT(o.id) AS antal_ordrar,
               SUM(o.antal * p.pris) AS total_intakt
        FROM butik.kunder k
        LEFT JOIN butik.ordrar o    ON o.kund_id = k.id
        LEFT JOIN butik.produkter p ON p.id = o.produkt_id
        GROUP BY k.id, k.namn
        ORDER BY total_intakt DESC NULLS LAST
    """).fetchall()
    con.close()
    return [{"kund_id": r[0], "namn": r[1], "antal_ordrar": r[2], "total_intakt": r[3] or 0} for r in rows]


@app.get("/api/statistik/basta-produkter")
async def basta_produkter():
    con = get_conn()
    rows = con.execute("""
        SELECT p.id, p.namn, p.pris,
               COALESCE(SUM(o.antal), 0)            AS sålda_enheter,
               COALESCE(SUM(o.antal * p.pris), 0)   AS total_intakt
        FROM butik.produkter p
        LEFT JOIN butik.ordrar o ON o.produkt_id = p.id
        GROUP BY p.id, p.namn, p.pris
        ORDER BY sålda_enheter DESC
    """).fetchall()
    con.close()
    return [{"produkt_id": r[0], "namn": r[1], "pris": r[2], "sålda_enheter": r[3], "total_intakt": r[4]} for r in rows]


@app.get("/api/statistik/ordrar-per-dag")
async def ordrar_per_dag():
    con = get_conn()
    rows = con.execute("""
        SELECT CAST(skapad AS DATE) AS dag,
               COUNT(*)             AS antal_ordrar,
               SUM(o.antal * p.pris) AS daglig_intakt
        FROM butik.ordrar o
        JOIN butik.produkter p ON p.id = o.produkt_id
        GROUP BY dag
        ORDER BY dag DESC
    """).fetchall()
    con.close()
    return [{"dag": str(r[0]), "antal_ordrar": r[1], "daglig_intakt": r[2]} for r in rows]


# ── JOINS ─────────────────────────────────────────────────────────────────────

@app.get("/api/kunder/{kund_id}/ordrar")
async def kunds_ordrar(kund_id: int):
    con = get_conn()
    kund = con.execute("SELECT id, namn, email FROM butik.kunder WHERE id = ?", [kund_id]).fetchone()
    if not kund:
        raise HTTPException(status_code=404, detail="Kund hittades inte")
    rows = con.execute("""
        SELECT o.id, p.namn, p.pris, o.antal, o.antal * p.pris AS delsumma, o.skapad
        FROM butik.ordrar o
        JOIN butik.produkter p ON p.id = o.produkt_id
        WHERE o.kund_id = ?
        ORDER BY o.skapad DESC
    """, [kund_id]).fetchall()
    con.close()
    ordrar = [{"order_id": r[0], "produkt": r[1], "pris": r[2], "antal": r[3], "delsumma": r[4], "skapad": str(r[5])} for r in rows]
    return {"kund": {"id": kund[0], "namn": kund[1], "email": kund[2]}, "ordrar": ordrar, "totalt": sum(o["delsumma"] for o in ordrar)}


@app.get("/api/produkter/{produkt_id}/ordrar")
async def produkts_ordrar(produkt_id: int):
    con = get_conn()
    produkt = con.execute("SELECT id, namn, pris FROM butik.produkter WHERE id = ?", [produkt_id]).fetchone()
    if not produkt:
        raise HTTPException(status_code=404, detail="Produkt hittades inte")
    rows = con.execute("""
        SELECT o.id, k.namn, k.email, o.antal, o.skapad
        FROM butik.ordrar o
        JOIN butik.kunder k ON k.id = o.kund_id
        WHERE o.produkt_id = ?
        ORDER BY o.skapad DESC
    """, [produkt_id]).fetchall()
    con.close()
    return {
        "produkt": {"id": produkt[0], "namn": produkt[1], "pris": produkt[2]},
        "ordrar": [{"order_id": r[0], "kund": r[1], "email": r[2], "antal": r[3], "skapad": str(r[4])} for r in rows]
    }


# ── DATASETS ──────────────────────────────────────────────────────────────────

INBYGGDA_DATASETS = [
    {"namn": "kunder",    "beskrivning": "Kundregister",          "källa": "inbyggd"},
    {"namn": "produkter", "beskrivning": "Produktkatalog",        "källa": "inbyggd"},
    {"namn": "ordrar",    "beskrivning": "Orderhistorik med join", "källa": "inbyggd"},
]


@app.get("/api/datasets")
async def lista_datasets():
    con = get_conn()
    tabeller = con.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'butik'
          AND table_name NOT IN ('kunder', 'produkter', 'ordrar')
        ORDER BY table_name
    """).fetchall()
    con.close()
    uppladdade = [{"namn": r[0], "beskrivning": "Uppladdad fil", "källa": "uppladdad"} for r in tabeller]
    return INBYGGDA_DATASETS + uppladdade


@app.get("/api/datasets/{namn}")
async def hamta_dataset(namn: str, limit: int = 100):
    con = get_conn()
    tabeller = [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'butik'"
    ).fetchall()]
    if namn not in tabeller:
        con.close()
        raise HTTPException(status_code=404, detail=f"Dataset '{namn}' hittades inte")
    kolumner = [r[0] for r in con.execute(
        f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'butik' AND table_name = '{namn}' ORDER BY ordinal_position"
    ).fetchall()]
    rows = con.execute(f"SELECT * FROM butik.{namn} LIMIT {limit}").fetchall()
    con.close()
    return {
        "namn": namn,
        "kolumner": kolumner,
        "antal_rader": len(rows),
        "data": [dict(zip(kolumner, r)) for r in rows]
    }


@app.post("/api/datasets/upload", status_code=201, dependencies=[Depends(kontrollera_nyckel)])
async def ladda_upp_dataset(fil: UploadFile = File(...), tabellnamn: str = Form(...)):
    if not tabellnamn.isidentifier():
        raise HTTPException(status_code=400, detail="Ogiltigt tabellnamn — använd bara bokstäver, siffror och _")
    suffix = ".csv" if fil.filename.endswith(".csv") else ".parquet"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await fil.read())
        tmp_path = tmp.name
    try:
        con = get_conn()
        if suffix == ".csv":
            con.execute(f"CREATE TABLE butik.{tabellnamn} AS SELECT * FROM read_csv_auto(?)", [tmp_path])
        else:
            con.execute(f"CREATE TABLE butik.{tabellnamn} AS SELECT * FROM read_parquet(?)", [tmp_path])
        con.close()
    finally:
        os.unlink(tmp_path)
    return {"namn": tabellnamn, "fil": fil.filename, "status": "skapad"}
