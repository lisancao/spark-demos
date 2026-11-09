from pyspark import pipelines as dp
from pyspark.sql.functions import col, from_json

CHANGE = "dish_id INT, dish STRING, price DECIMAL(5,2), station STRING, seq BIGINT, op STRING"

# The raw change feed: one JSON event per menu change, on a Kafka topic.
@dp.table
def menu_changes():
    return (spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", "localhost:29292")
        .option("subscribe", "menu-changes")
        .option("startingOffsets", "earliest")
        .load()
        .select(from_json(col("value").cast("string"), CHANGE).alias("e"))
        .select("e.*"))
