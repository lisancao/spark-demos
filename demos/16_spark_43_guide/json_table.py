from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
order = """'{"id": 7, "items": [{"sku": "A1", "qty": 2, "gift": true},
                                {"sku": "B9", "qty": 1}]}'"""

# JSON_TABLE: expand the array and type each field, in one table function
spark.sql(f"""
  SELECT * FROM JSON_TABLE({order}, '$.items[*]' COLUMNS (
      line FOR ORDINALITY, sku STRING, qty INT, gift BOOLEAN EXISTS))
""").show()
