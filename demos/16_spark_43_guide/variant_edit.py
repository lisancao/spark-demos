from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()
spark.sql("""SELECT parse_json('{"plan": "free", "tags": ["beta"],
                                 "ssn": "0000", "ref": null}') AS v""") \
     .createOrReplaceTempView("profiles")

# Edit a VARIANT in place: no parsing into a struct and back
edits = {
    "set":      "variant_set(v, '$.plan', 'pro'::variant)",
    "deleted":  "variant_delete(v, '$.ssn')",
    "appended": "variant_array_append(v, '$.tags', 'early'::variant)",
    "stripped": "variant_strip_nulls(v)",
}
for name, expr in edits.items():
    row = spark.sql(f"SELECT to_json({expr}) FROM profiles").first()
    print(f"{name:9}", row[0])
