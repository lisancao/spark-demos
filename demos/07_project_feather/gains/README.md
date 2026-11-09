# What single-task execution saves (Spark 4.3)

Benchmarks behind the post on Project Feather's shuffle-free single-task execution
(`spark.sql.optimizer.singleTaskExecution.enabled`, SPARK-57851). Run from `demos/07_project_feather`
with a PySpark 4.3.0 venv:

```bash
python gains/stages.py                      # stages run vs skipped, rebuilt vs reused DataFrame
python gains/warm.py 50 gains/results-warm-1.json   # six query shapes, rebuilt and reused, flag off/on
python gains/cold.py true "group by, order by"      # one fresh session, first query (run per process)
python gains/suite.py true 200 pandas       # 200 tiny test cases; fixtures from list or pandas
```

`queries.py` writes the 1,000-row test file to `gains/data/` and defines the query shapes.
`cache.py` (Arrow cache serializer) is unfinished: the compressed runs hung on 2026-11-06.

Measured 2026-11-06: pyspark 4.3.0, local[*], AMD Ryzen 7 7800X3D (16 threads), OpenJDK 17.0.20,
Python 3.14, Linux. Results: `results-*.json*`, `results-stages.txt`.
