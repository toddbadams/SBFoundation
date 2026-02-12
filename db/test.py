import duckdb

# In-memory DB
con = duckdb.connect()
value = con.execute("SELECT 42 AS answer").fetchone()[0]
print("answer:", value)

# File-backed DB (creates ./local.duckdb)
db_path = "local.duckdb"
con2 = duckdb.connect(db_path)
con2.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER, name VARCHAR)")
con2.execute("INSERT INTO t VALUES (1, 'Todd')")
rows = con2.execute("SELECT * FROM t").fetchall()
print("rows:", rows)
con2.close()
