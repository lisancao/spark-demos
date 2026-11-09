"""What a collect actually runs: stages executed vs skipped, for a rebuilt and a reused DataFrame."""
import sys
from pyspark.sql import SparkSession
sys.path.insert(0, "gains"); from queries import queries
spark = SparkSession.builder.getOrCreate()
sc = spark.sparkContext
FLAG = "spark.sql.optimizer.singleTaskExecution.enabled"

N = iter(range(10**6))
def run(f):
    tr = sc.statusTracker(); g = f"probe-{next(N)}"
    sc.setJobGroup(g, g); f(); sc._jsc.clearJobGroup()
    jobs = tr.getJobIdsForGroup(g)
    ran = skipped = tasks = 0
    for j in jobs:
        for s in tr.getJobInfo(j).stageIds:
            i = tr.getStageInfo(s)
            if i is None or i.numCompletedTasks == 0: skipped += 1
            else: ran += 1; tasks += i.numCompletedTasks
    return {"jobs": len(jobs), "stages run": ran, "stages skipped": skipped, "tasks": tasks}

build = queries(spark)["distinct, group, order"]
for v in ("false", "true"):
    spark.conf.set(FLAG, v)
    df = build(); df.collect()
    import time; time.sleep(0.5)
    a = run(lambda: build().collect()); time.sleep(0.5)
    b = run(lambda: df.collect()); time.sleep(0.5)
    print(f"flag {v}: rebuilt {a}   reused {b}")
