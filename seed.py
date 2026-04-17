from database import get_conn, init_db

init_db()
con = get_conn()

# Rensa befintlig data
con.execute("DELETE FROM ordrar")
con.execute("DELETE FROM produkter")
con.execute("DELETE FROM kunder")

con.executemany("INSERT INTO kunder VALUES (?, ?, ?, ?)", [
    (1, "Anna Svensson",   "anna@example.com",  "070-1234567"),
    (2, "Erik Johansson",  "erik@example.com",  "073-9876543"),
    (3, "Maria Lindqvist", "maria@example.com", "076-5551234"),
])

con.executemany("INSERT INTO produkter VALUES (?, ?, ?, ?)", [
    (1, "Laptop",       9999.0, 15),
    (2, "Hörlurar",      799.0, 50),
    (3, "Tangentbord",  1299.0, 30),
    (4, "Mus",           399.0, 80),
])

con.executemany("INSERT INTO ordrar (id, kund_id, produkt_id, antal) VALUES (?, ?, ?, ?)", [
    (1, 1, 1, 1),
    (2, 1, 2, 2),
    (3, 2, 3, 1),
    (4, 3, 4, 3),
])

con.close()
print("Databasen seedades! Kunder, produkter och ordrar tillagda.")
