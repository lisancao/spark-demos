from pyspark.sql import SparkSession
from plan_summary import operators  # the plan's operators, one per line
from pyspark.sql.functions import udf

spark = (SparkSession.builder
         .config("spark.sql.ansi.enabled", "true")  # transpiling needs ANSI
         .getOrCreate())
df = spark.createDataFrame([("birria tacos",), ("khao soi",)], "dish string")

for transpile in ("false", "true"):
    spark.conf.set("spark.sql.experimental.optimizer.transpilePyUDFs",
                   transpile)

    @udf("int", useArrow=False)
    def name_length(dish: str) -> int:
        return len(dish)

    q = df.select(name_length("dish").alias("n"))
    q.collect()
    print(f"transpilePyUDFs={transpile}\n{operators(q)}")
    python = "BatchEvalPython" in operators(q)
    print("  n computed by:", "a Python worker" if python
          else "Spark's own length()", "\n")
