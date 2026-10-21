"""A dashboard over a metric view, with no formula in it.

    streamlit run apps/dashboard.py

The app reads the definition of every metric view from the catalog (DESCRIBE TABLE EXTENDED),
offers the dimensions and measures as controls, and runs the MEASURE() query for whatever is
picked. It never computes a number itself.
"""

from __future__ import annotations

import os

import altair as alt
import streamlit as st
import yaml
from pyspark.sql import SparkSession

REMOTE = os.environ.get("SPARK_REMOTE", "sc://localhost:15002")


@st.cache_resource
def session() -> SparkSession:
    return SparkSession.builder.remote(REMOTE).getOrCreate()


@st.cache_data(ttl=60)
def metric_views() -> dict[str, str]:
    """Metric view name -> its YAML definition, straight from the catalog."""
    spark = session()
    found = {}
    for view in spark.sql("SHOW VIEWS").collect():
        name = f"{view.namespace}.{view.viewName}"
        info = {
            r.col_name: r.data_type for r in spark.sql(f"DESCRIBE TABLE EXTENDED {name}").collect()
        }
        if info.get("Type") == "METRIC_VIEW":
            found[name] = info["View Text"]
    return found


st.set_page_config(page_title="Delivery metrics", layout="wide")
st.title("Delivery metrics")
st.caption(f"Every number on this page is a `MEASURE()` over a metric view on {REMOTE}.")

views = metric_views()
if not views:
    st.warning("No metric views in the catalog. Run `make register` first.")
    st.stop()

name = st.sidebar.selectbox("Metric view", list(views))
definition = yaml.safe_load(views[name])
dimensions = [d["name"] for d in definition.get("dimensions", [])]
measures = [m["name"] for m in definition.get("measures", [])]
group_by = st.sidebar.multiselect("Group by", dimensions, default=dimensions[:1])
picked = st.sidebar.multiselect("Measures", measures, default=measures[:3])

if picked:
    select = ", ".join(group_by + [f"MEASURE({m}) AS {m}" for m in picked])
    sql = f"SELECT {select} FROM {name}"
    if group_by:
        sql += f" GROUP BY {', '.join(group_by)} ORDER BY {picked[0]} DESC"
    frame = session().sql(sql).toPandas()
    left, right = st.columns([3, 2])
    with left:
        st.dataframe(frame, hide_index=True)
    with right:
        if len(group_by) == 1 and len(frame) <= 40:
            chart = alt.Chart(frame).mark_bar().encode(x=alt.X(group_by[0], sort=None), y=picked[0])
            st.altair_chart(chart, use_container_width=True)
    st.code(sql, language="sql")

with st.expander("Definition, as stored in the catalog"):
    st.code(views[name], language="yaml")
