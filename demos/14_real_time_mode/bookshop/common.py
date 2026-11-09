"""Settings shared by every step of the demo."""
import os
import sys
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.types import LongType, StringType, StructField, StructType

DEMO = Path(__file__).resolve().parent.parent
DATA = DEMO / "data"
CATALOG = str(DATA / "catalog")            # Parquet: book_id, title, author, aisle, vector
CHECKPOINTS = DATA / "checkpoints"

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:29192")
CLICKS = "clicks"          # shopper events in
ENRICHED = "enriched"      # step 2 output
TRENDING = "trending"      # step 3 output
RECS = "recs"              # step 4 output (Scala)

SPARK_VERSION = "4.3.0"
KAFKA_PACKAGE = f"org.apache.spark:spark-sql-kafka-0-10_2.13:{SPARK_VERSION}"

# One shopper event, as the generator writes it to the `clicks` topic.
CLICK_SCHEMA = StructType([
    StructField("event_id", StringType()),
    StructField("user_id", StringType()),
    StructField("book_id", LongType()),
    StructField("action", StringType()),     # view | cart | purchase
    StructField("ts", LongType()),           # epoch millis, set by the shopper
])


def spark(app: str, cores: int = 16) -> SparkSession:
    os.environ.setdefault("PYSPARK_PYTHON", sys.executable)   # workers use this venv too
    b = SparkSession.builder
    # Internal 4.3 knob: how long a part-filled streaming-shuffle buffer may wait before it is
    # flushed to the stateful task (default 50 ms). Only set when measuring its effect.
    if os.environ.get("SHUFFLE_WAIT_MS"):
        b = b.config("spark.shuffle.streaming.networkBufferMaxWaitTimeMs", os.environ["SHUFFLE_WAIT_MS"])
    return (
        b.appName(app)
        .master(f"local[{cores}]")
        .config("spark.jars.packages", KAFKA_PACKAGE)
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.python.worker.faulthandler.enabled", "true")
        # The state store Real-time Mode picks by itself, set for both modes so they compare fairly.
        .config("spark.sql.streaming.stateStore.providerClass",
                "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider")
        .config("spark.sql.streaming.stateStore.rocksdb.changelogCheckpointing.enabled", "true")
        .config("spark.sql.streaming.stateStore.checkpointFormatVersion", "2")
        .getOrCreate()
    )
