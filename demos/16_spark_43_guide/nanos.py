from pyspark.sql import SparkSession

spark = (SparkSession.builder
         .config("spark.sql.timestampNanosTypes.enabled", "true")  # preview
         .getOrCreate())

# Two trades, one nanosecond apart
spark.sql("""
  SELECT CAST(t AS TIMESTAMP_NTZ)    AS micros,    -- the old precision
         CAST(t AS TIMESTAMP_NTZ(9)) AS nanos,     -- new in 4.3
         unix_nanos(CAST(t AS TIMESTAMP_NTZ(9))) AS unix_nanos
  FROM VALUES ('2026-11-05 09:30:00.000000001'),
              ('2026-11-05 09:30:00.000000002') AS trades(t)
""").createOrReplaceTempView("trades")

spark.table("trades").show(truncate=False)
# At microseconds they collide; at nanoseconds they stay two trades
spark.sql("""SELECT micros, count(*) AS trades,
                    count(DISTINCT nanos) AS distinct_nanos
             FROM trades GROUP BY micros""").show(truncate=False)
