# Film: DSv2 filter pushdown (IntelliJ)

**Story.** Spark offers a connector every filter it could push; the connector keeps
what it can apply and hands the rest back. One breakpoint in
`CsvScanBuilder.pushFilters` shows the whole exchange, and the physical plan agrees
with it. This is the first breakpoint `IDEA_SETUP.md` recommends.

**Take:** `take.sh`. **Needs:** the film profile (`kit/ide/make-profile.sh` in the film-demo skill), the
project opened once with `setup-idea.sh` run, and `SPARK_HOME` in the run configuration
pointing at a Spark 4.2 install (the pyspark in demo 01's `.venv` works).

## Beats

There is no video script for this demo yet, so the VO lines are drafts sized for timing,
not final copy. Each hold leaves room for its line at 150 words a minute.

`focus` is the box (x, y, width, height on the 2560x1440 film display) that the vertical
cut zooms into over a blurred copy of the whole frame. Keep boxes under about 1500
px wide: the box is scaled to 1040 px, and wider boxes make the text too small for a
phone. Measure them on a frame of `take-raw.mp4`, not on a guess.

| beat | shows | VO | focus | zoom |
|---|---|---|---|---|
| `open` | `BeforeAfterDemo`: the V2 read, the `dept = eng` filter, the demo's note about the plan | The demo reads the same CSV twice, once through the old V1 API and once through a DataSource V2 connector. This is the V2 query: select name, keep the rows where dept equals eng. | 270,330,1540,680 | `code 2-end` |
| `goto` | Jump to `CsvScanBuilder` with Ctrl+Shift+N, `50G zt` | The connector's ScanBuilder is where Spark negotiates the scan. | 270,330,1540,680 |  |
| `contract` | The `pushFilters` javadoc and method | Spark offers every filter it could push. pushFilters returns the ones the connector doesn't handle, so Spark keeps evaluating those itself. This connector handles equality on string columns and nothing else. | 230,200,1400,720 | `doc 1-end` |
| `breakpoint` | Ctrl+F8 on line 70, after the loop has sorted the filters | Break once it has sorted them. | 230,200,1400,720 | `doc 0-end` |
| `debug` | Debug the run configuration; it stops on line 70 with inline values | Run it under the debugger. Spark plans the query and stops inside the connector. | 230,190,1500,600 | `frame 4-end` |
| `variables` | `filters`, `accepted`, `rejected` expanded in the Variables pane | Spark offered two filters: dept is not null, and dept equals eng. The connector kept the equality and handed the not-null check back. | 560,1090,1180,290 | `vars 1-end` |
| `plan` | The console, searched for `pushedFilters=1)`: the BatchScan line, and `Filter isnotnull(dept)` above it | The physical plan agrees. The scan reports one pushed filter, and Spark still runs the not-null check itself, because the connector declined it. | 240,1080,1300,190 | `plan 2-end` |

`zoom` drives the landscape cut's dynamic zoom (`film.py zoom`): a region from the table
below and the seconds into the beat it holds, `end` being the end of the beat. The
camera eases in, pans straight to the next region when the gap is under 1.5s, and eases
out otherwise. Boxes are in the same 2560x1440 space as `focus`.

| region | landscape | vertical |
|---|---|---|
| `code` | 270,330,1540,680 | - |
| `doc` | 230,200,1400,720 | - |
| `frame` | 230,190,1500,600 | - |
| `vars` | 560,1090,1180,290 | - |
| `plan` | 240,1080,1300,190 | - |

## What has to be readable

- `variables`: `IsNotNull(dept)` and `EqualTo(dept,eng)` under `filters`, one entry each
  under `accepted` and `rejected`.
- `plan`: `pushedFilters=1` in the BatchScan line and `Filter isnotnull(dept)` on the
  line above it, together.
