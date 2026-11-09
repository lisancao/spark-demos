import sys; sys.path.insert(0, "bin")
from lake import lake

spark = lake()
# Every version of every dish, with the window it was true for.
spark.sql("""
    SELECT dish_id, dish, price, station, __START_AT, __END_AT
    FROM lake.kitchen.menu
    ORDER BY dish_id, __START_AT
""").show(truncate=False)
