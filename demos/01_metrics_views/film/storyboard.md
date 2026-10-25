# Film: metric views (terminal)

**Story.** Two aggregation errors that are valid SQL, one definition in the catalog that
fixes both, and the one error it can't prevent. The beats follow the reel script
(`video_metric_views_reel.md`), and every number on screen comes from a live run against
the demo's Spark 4.2.0 Connect server.

**Tape:** `metric_views.tape`. **Needs:** `make up` in this folder (the Connect server)
and the demo's `.venv`.

## Beats

Each beat is one clip. The hold is sized so the VO line fits over the beat at a calm
150 words a minute; `film.py render` warns when a clip is shorter than its VO. The VO
column is the reel's spoken text, so the clips and the teleprompter line up. Where the
reel cuts to a graphic, the graphic's part of the chapter isn't in the beat's VO.

| beat | shows | VO | hold | zoom |
|---|---|---|---|---|
| `open` | A comment line: live numbers, Spark 4.2.0 | Spark four point two adds metric views. In the next five minutes: the two aggregation errors they're designed for, how to define one, and the one thing they don't prevent. | 12s |  |
| `browse` | yazi over `examples/`, each script's code in the preview | | 12s |  |
| `average` | Example 01 opens in nvim; `:Run` puts its output beside the queries: 0.2384 against 0.0923, ratio 2.6 | Here's a month of sessions for a food delivery service, split into five regions, each with its own conversion rate. Average the five rates, and you get twenty-three point eight percent. Divide total conversions by total sessions, and you get nine point two percent. | 28s | `avg-code 7.5-15; avg-rates 17-21.5; avg-totals 22.5-end-1` |
| `distinct` | Example 02's queries, then its output beside them: 69420 against 9994 | Second error. Add up thirty days of distinct users and you get sixty-nine thousand four hundred twenty. Count distinct users over the month and it's nine thousand nine hundred ninety-four. Each user is counted once for every day they showed up. | 26s | `dist-code 7.5-13.5; dist-out 15-end-1` |
| `define` | nvim on example 03, the file tree beside it, walking down the YAML | A metric view puts the formula in the catalog. You write CREATE VIEW, WITH METRICS, LANGUAGE YAML, and a YAML definition. The definition names a source table, dimensions to group by, and measures. Conversion rate is converted sessions over sessions. Active users is a distinct count. | 21s |  |
| `create` | Example 03 runs and registers the view | In Spark four point two point oh, the version must be zero point one, and each dimension and measure has just a name and an expression. | 10s |  |
| `grain` | Example 04's queries, then the same measures for the month and by region | To query it, wrap each measure in MEASURE. For the whole month, conversion rate is nine point two percent and active users is nine thousand nine hundred ninety-four. Group by region, and each region gets its own correct rate. | 27s | `grain-code 7.5-14; grain-month 16-19.5; grain-region 20.5-end-1` |
| `limit` | Example 05's queries; summing MEASURE by day gives 69420 again | Here's the limit. Ask for active users by day with MEASURE, then add those numbers up in an outer query, and you get sixty-nine thousand four hundred twenty again. The result of MEASURE is an ordinary column, and summing it is ordinary SQL. So ask for each measure at the grain you report. | 31s | `limit-code 7.5-15.5; limit-sum 17.5-end-1` |

`zoom` is the landscape cut's dynamic zoom (`film.py zoom`): a region from the table
below and the seconds into the beat it holds, `end-1` being a second before the beat
ends. Each example opens on its queries, full width, and `:Run` (the film nvim config)
splits the output in beside them, so the zoom goes from the code to the table the VO is
reading. Boxes are pixels of the 1920x1080 landscape render, measured on its frames. The
vertical cut stacks code over output at a bigger font and isn't zoomed.

| region | landscape | vertical |
|---|---|---|
| `avg-code` | 30,30,1150,620 | - |
| `avg-rates` | 1066,40,640,300 | - |
| `avg-totals` | 1066,360,800,180 | - |
| `dist-code` | 30,30,1150,620 | - |
| `dist-out` | 1066,40,830,500 | - |
| `grain-code` | 30,30,1000,560 | - |
| `grain-month` | 1066,40,560,200 | - |
| `grain-region` | 1066,250,640,320 | - |
| `limit-code` | 30,280,1150,300 | - |
| `limit-sum` | 1066,250,640,180 | - |

## What has to be readable

- `average`: the three-column table with 0.2384, 0.0923 and 2.6.
- `grain`: example 04 prints two tables; the first table's header must stay on screen
  (font 22 with line height 1.0 fits it at 1080p).
- `define`: the YAML from `version: 0.1` to the last measure, in the frame at once.

## Not filmed here

The title card, the end card and the reel's graphics (`03_average_of_ratios.svg` and the
rest) are the editor's. The reel's second half of chapter 2 and of chapter 1 runs over
those graphics, which is why those VO cells stop where the terminal part ends.
