# Metric views, filmed from the reel's five examples. Storyboard: storyboard.md.
#   film/kit/film.py render demos/01_metrics_views/film/metric_views.tape [--format vertical]
#   film/kit/film.py real   demos/01_metrics_views/film/metric_views.tape
# Needs the demo's Connect server (make up) and .venv.
Set TypingSpeed 45ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip: the demo folder, its venv, comments
# allowed, the film nvim config. The short prompt is for VHS; the real pass keeps hers.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 && source .venv/bin/activate && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua'" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}01_metrics_views%f %F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: open | Live numbers, Spark 4.2.0
Sleep 800ms
Type "# Metric views, Spark 4.2.0. Every number below is a live run." Enter
Sleep 9s

# beat: browse | The five examples
Hide
Ctrl+L
Show
Sleep 600ms
Type "yazi examples"
Sleep 300ms
Enter
# yazi takes a few seconds to query the terminal; cut over the wait.
Hide
Sleep 6s
Show
Sleep 2s
Down@1.8s 4
Sleep 1.5s
Up@400ms 4
Sleep 800ms
Type "q"
Sleep 600ms

# beat: average | Averaging rates
Hide
Ctrl+L
Show
Sleep 600ms
Type "# 1. Average the five regional rates, or divide total conversions by total sessions?" Enter
Sleep 800ms
Type "nvim examples/01_average_of_ratios.py"
Sleep 300ms
Enter
# Off camera: nvim's startup and framing the queries (scrolloff would keep lines above).
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "18G"
Type "zt"
Sleep 400ms
Show
Sleep 8s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@90s /Process exited/
Sleep 12s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: distinct | Summing distinct counts
Hide
Ctrl+L
Show
Sleep 600ms
Type "# 2. Add up daily distinct users, or count distinct users for the month?" Enter
Sleep 800ms
Type "nvim examples/02_summing_distinct_counts.py"
Sleep 300ms
Enter
# Off camera: nvim's startup and framing the queries (scrolloff would keep lines above).
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "20G"
Type "zt"
Sleep 400ms
Show
Sleep 6s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@90s /Process exited/
Sleep 12s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: define | One definition, in YAML
Hide
Ctrl+L
Show
Sleep 600ms
Type "# 3. Put each formula in the catalog once, as a metric view." Enter
Sleep 800ms
Type "nvim examples/03_create_metric_view.py"
Sleep 300ms
Enter
# Off camera: nvim's startup, opening the tree and framing the YAML.
Hide
Sleep 2.5s
Type " e"
Sleep 800ms
Ctrl+W
Type "l"
Sleep 300ms
Type "17G"
Type "zt"
Sleep 500ms
Show
Sleep 4s
Down@450ms 22
Sleep 5s
Type ":qa"
Sleep 300ms
Enter
Sleep 500ms

# beat: create | Registering the view
Hide
Ctrl+L
Show
Sleep 600ms
Type "python examples/03_create_metric_view.py" Enter
Wait
Sleep 6s

# beat: grain | MEASURE() at every grain
Hide
Ctrl+L
Show
Sleep 600ms
Type "# 4. MEASURE() evaluates each formula at the grain the query asks for." Enter
Sleep 800ms
Type "nvim examples/04_measure_at_every_grain.py"
Sleep 300ms
Enter
# Off camera: nvim's startup and framing the queries (scrolloff would keep lines above).
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "16G"
Type "zt"
Sleep 400ms
Show
Sleep 7s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@90s /Process exited/
Sleep 12s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: limit | What it does not prevent
Hide
Ctrl+L
Show
Sleep 600ms
Type "# 5. The limit: MEASURE() returns an ordinary column, and summing it is ordinary SQL." Enter
Sleep 800ms
Type "nvim examples/05_what_it_does_not_prevent.py"
Sleep 300ms
Enter
# Off camera: nvim's startup and framing the queries (scrolloff would keep lines above).
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "16G"
Type "zt"
Sleep 400ms
Show
Sleep 8s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@90s /Process exited/
Sleep 14s
Hide
Type ":qa!" Enter
Sleep 500ms
