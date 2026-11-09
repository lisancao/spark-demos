"""Step 0 (batch): build the shop's catalog and embed every book once.

Project Gutenberg's catalog becomes a 12-aisle bookshop. Each book's text (title,
author, subject headings) goes through a small embedding model inside Spark with
mapInPandas; the vectors are what the streaming recommender scores against later.
The aisle label is deliberately NOT part of the embedded text, so the hit-rate
check in step 4 can't be won by reading the answer key.
"""
from typing import Iterator

import pandas as pd
from pyspark.sql import functions as F
from pyspark.sql.window import Window

from bookshop.common import CATALOG, DATA, spark

AISLES = [
    "Science-Fiction & Fantasy", "Crime, Thrillers and Mystery", "Poetry",
    "Mythology, Legends & Folklore", "Romance", "Cooking & Drinking",
    "Travel Writing", "Philosophy & Ethics", "History - Ancient",
    "Science - Physics", "Plays/Films/Dramas", "Nature/Gardening/Animals",
]
PER_AISLE = 500
MODEL = "BAAI/bge-small-en-v1.5"   # 384 dimensions, MIT licence


def embed(batches: Iterator[pd.DataFrame]) -> Iterator[pd.DataFrame]:
    from fastembed import TextEmbedding
    model = TextEmbedding(MODEL, cache_dir=str(DATA / "models"), threads=1)   # one core per Spark task
    for pdf in batches:
        vectors = list(model.embed(pdf["text"].tolist(), batch_size=64))
        yield pdf.drop(columns=["text"]).assign(vector=[v.astype("float32").tolist() for v in vectors])


def main() -> None:
    from fastembed import TextEmbedding
    TextEmbedding(MODEL, cache_dir=str(DATA / "models"))   # download once, before 16 workers want it
    s = spark("catalog")
    raw = (s.read.option("header", True).option("multiLine", True).option("escape", '"')
           .csv(str(DATA / "pg_catalog.csv.gz")))

    aisles = F.array(*[F.lit(a) for a in AISLES])
    cats = F.transform(F.split("Bookshelves", ";\\s*"), lambda c: F.regexp_replace(c, "^Category: ", ""))
    books = (raw.where("Language = 'en' AND Type = 'Text' AND Subjects IS NOT NULL")
             .withColumn("in_aisles", F.array_intersect(cats, aisles))
             .where(F.size("in_aisles") == 1)            # exactly one aisle: an unambiguous label
             .select(F.col("Text#").cast("long").alias("book_id"),
                     F.regexp_replace("Title", "\\s+", " ").alias("title"),
                     F.coalesce(F.regexp_extract("Authors", "^([^,;]+)", 1), F.lit("")).alias("author"),
                     F.col("in_aisles")[0].alias("aisle"),
                     F.concat_ws(". ", F.regexp_replace("Title", "\\s+", " "), "Authors", "Subjects").alias("text")))

    # Up to PER_AISLE books per aisle, chosen by a hash so reruns pick the same ones.
    ranked = books.withColumn("rn", F.row_number().over(
        Window.partitionBy("aisle").orderBy(F.xxhash64("book_id"))))
    shop = ranked.where(F.col("rn") <= PER_AISLE).drop("rn").repartition(16)

    out_schema = "book_id long, title string, author string, aisle string, vector array<float>"
    shop.mapInPandas(embed, out_schema).repartition(1).write.mode("overwrite").parquet(CATALOG)

    cat = s.read.parquet(CATALOG)
    cat.groupBy("aisle").count().orderBy("aisle").show(truncate=False)
    print("books:", cat.count(), " dims:", cat.select(F.size("vector")).first()[0])


if __name__ == "__main__":
    main()
