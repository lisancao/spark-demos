"""One fresh session, one query, timed from the first collect: run once per process."""
import json, sys, time
from pyspark.sql import SparkSession
sys.path.insert(0, "gains"); from queries import queries
flag, name = sys.argv[1], sys.argv[2]
t0 = time.perf_counter()
spark = (SparkSession.builder
         .config("spark.sql.optimizer.singleTaskExecution.enabled", flag).getOrCreate())
t1 = time.perf_counter()
queries(spark)[name]().collect()
t2 = time.perf_counter()
print(json.dumps({"flag": flag, "query": name, "session_ms": round((t1-t0)*1000, 1), "first_query_ms": round((t2-t1)*1000, 1)}))
