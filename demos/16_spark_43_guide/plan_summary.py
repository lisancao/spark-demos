"""Print an executed plan as its operator names, one per line, without the attribute noise."""
import re


# Plan bookkeeping that doesn't change what the query does.
HIDDEN = {"AdaptiveSparkPlan", "Final", "Initial", "ResultQueryStage", "AQEShuffleRead",
          "ShuffleQueryStage", "ColumnarToRow", "InputAdapter", "WholeStageCodegen"}


def operators(df):
    """The executed plan's operators, one per line, without the attribute noise."""
    plan = df._jdf.queryExecution().executedPlan().toString()
    final = plan.split("== Initial Plan ==")[0]
    out = []
    for line in final.splitlines():
        m = re.match(r"^([\s:+\-]*)(\*\(\d+\)\s*)?([A-Za-z]+)(\s+(hashpartitioning|rangepartitioning|SinglePartition))?", line)
        if not m or m.group(3) in HIDDEN:
            continue
        out.append("  " * len(out) + m.group(3) + (f" ({m.group(5)})" if m.group(5) else ""))
    return "\n".join(out)
