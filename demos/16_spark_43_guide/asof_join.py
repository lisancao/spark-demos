from pyspark.sql import SparkSession

spark = (SparkSession.builder
         .config("spark.sql.join.asofJoin.enabled", "true")  # preview flag
         .getOrCreate())

spark.sql("""
  SELECT p.made_at, p.score, f.version AS features_used, f.published_at
  FROM VALUES (TIMESTAMP '2026-11-05 10:03', 0.91),
              (TIMESTAMP '2026-11-05 10:07', 0.42) AS p(made_at, score)
  ASOF JOIN VALUES (TIMESTAMP '2026-11-05 10:00', 'v1'),
                   (TIMESTAMP '2026-11-05 10:05', 'v2')
                   AS f(published_at, version)
  MATCH_CONDITION (p.made_at >= f.published_at)  -- latest one out by then
""").show()
