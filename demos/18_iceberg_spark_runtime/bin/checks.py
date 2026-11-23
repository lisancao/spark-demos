"""Which statements need the Iceberg SQL extensions on this Spark?

Run inside the Spark container by bin/run.sh, with the extensions on or off. Each
statement runs on its own and prints [ok] or [fail] with the first error line, so one
failure does not stop the rest.
"""
import sys

from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
ext = spark.conf.get("spark.sql.extensions", "") or "(none)"
print(f"spark {spark.version}, spark.sql.extensions = {ext}")

STATEMENTS = [
    ("drop the table from the last run", "DROP TABLE IF EXISTS demo.shop.books PURGE"),
    ("DROP VIEW (cleanup from the last run)", "DROP VIEW IF EXISTS demo.shop.low_stock"),
    ("create a v3 table", "CREATE TABLE demo.shop.books (id BIGINT, stock INT) USING iceberg TBLPROPERTIES ('format-version'='3')"),
    ("INSERT", "INSERT INTO demo.shop.books VALUES (1, 3), (2, 0)"),
    ("MERGE INTO (v3 table)", """MERGE INTO demo.shop.books t
        USING (SELECT * FROM VALUES (2L, 5), (3L, 2) AS s(id, stock)) s ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET t.stock = t.stock + s.stock
        WHEN NOT MATCHED THEN INSERT *"""),
    ("row lineage after MERGE", "SELECT id, stock, _row_id, _last_updated_sequence_number FROM demo.shop.books ORDER BY id"),
    ("UPDATE", "UPDATE demo.shop.books SET stock = 0 WHERE id = 1"),
    ("DELETE", "DELETE FROM demo.shop.books WHERE stock = 0"),
    ("CALL rewrite_data_files", "CALL demo.system.rewrite_data_files(table => 'shop.books')"),
    ("CREATE VIEW", "CREATE VIEW demo.shop.low_stock AS SELECT id FROM demo.shop.books WHERE stock < 3"),
    ("ALTER TABLE ... CREATE BRANCH", "ALTER TABLE demo.shop.books CREATE BRANCH IF NOT EXISTS audit"),
    ("ALTER TABLE ... WRITE ORDERED BY", "ALTER TABLE demo.shop.books WRITE ORDERED BY id"),
    ("metadata table", "SELECT operation FROM demo.shop.books.snapshots"),
]

for label, sql in STATEMENTS:
    try:
        rows = [tuple(r) for r in spark.sql(sql).collect()]
        print(f"[ok]   {label}: {rows[:4]}")
    except Exception as e:  # report the line that names the error
        lines = [l.strip() for l in str(e).splitlines() if l.strip()]
        first = next((l for l in lines if "Exception" in l or "Error" in l or "[" in l[:2]), lines[0])
        print(f"[fail] {label}: {first[:220]}")
spark.stop()
sys.exit(0)
