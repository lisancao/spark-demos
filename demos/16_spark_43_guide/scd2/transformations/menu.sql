-- Keep every version of every dish, not just the latest one.
CREATE STREAMING TABLE menu
FLOW AUTO CDC
FROM STREAM(menu_changes)
KEYS (dish_id)
SEQUENCE BY seq
APPLY AS DELETE WHEN op = 'DELETE'
COLUMNS * EXCEPT (op)
STORED AS SCD TYPE 2
TRACK HISTORY ON (price, station);
