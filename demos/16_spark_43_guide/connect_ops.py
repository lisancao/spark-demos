from pyspark.sql import SparkSession

# New in 4.3: a Connect session works as a context manager
remote = SparkSession.builder.remote("sc://localhost:15043")
with remote.getOrCreate() as spark:
    ok = spark.sql("SELECT count(*) AS n FROM range(1000000)")
    ok.collect()
    print("succeeded, operation", ok.executionInfo.operation_id)

    try:
        spark.sql("SELECT revenue FROM range(10)").collect()
    except Exception as e:   # the client knows the ID even on failure
        print("failed,    operation", e.operation_id)
        open("data/failed_op", "w").write(e.operation_id)
