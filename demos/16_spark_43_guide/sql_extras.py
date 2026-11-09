from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
show = lambda q: spark.sql(q).show(truncate=False)

# ANSI UNNEST, with a position for each element
show("""SELECT * FROM UNNEST(array('bronze', 'silver', 'gold'))
        WITH ORDINALITY AS t(tier, pos)""")

# counter_diff: running counter -> deltas; a reset is NULL, not -125
show("""SELECT minute, requests,
               counter_diff(requests) OVER (ORDER BY minute) AS delta
        FROM VALUES (1, 100), (2, 130), (3, 5), (4, 40) t(minute, requests)""")

# jaro_winkler_similarity: fuzzy matching for messy names
score = spark.sql("SELECT jaro_winkler_similarity('Databricks', 'DataBricks')")
print("jaro_winkler_similarity:", round(score.first()[0], 3))
