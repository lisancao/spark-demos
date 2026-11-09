# The Ultimate Guide to Apache Spark 4.3: SCD Type 2 in Auto CDC. Storyboard: storyboard.md.
#   film render demos/16_spark_43_guide/film/scd2.tape --format square
Set TypingSpeed 40ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 FILM_RUN_PYTHON=.venv/bin/python SPARK_LOCAL_IP=127.0.0.1 PYSPARK_PYTHON=$PWD/.venv/bin/python SPARK_CONF_DIR=$PWD/conf && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua' && alias python=.venv/bin/python" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: scd2-flow | An Auto CDC flow that keeps history
Hide
Type "clear; scd2/reset.sh; clear" Enter
Wait@120s
Show
Type "batcat --style=plain --paging=never scd2/transformations/menu_changes.py" Enter
Sleep 7s
Hide
Type "clear" Enter
Show
Type "batcat --style=plain --paging=never scd2/transformations/menu.sql" Enter
Sleep 11s

# beat: scd2-v1 | Batch 1: two dishes
Hide
Type "clear" Enter
Show
Type "cat scd2/incoming/batch-1.json" Enter
Sleep 3s
Type "scd2/publish.sh scd2/incoming/batch-1.json && scd2/run.sh" Enter
Wait@180s
Type "scd2/history.sh" Enter
Wait@90s
Sleep 6s

# beat: scd2-v2 | Batch 2: a price rise, a station move, a new dish
Hide
Type "clear" Enter
Show
Type "cat scd2/incoming/batch-2.json" Enter
Sleep 3s
Type "scd2/publish.sh scd2/incoming/batch-2.json && scd2/run.sh" Enter
Wait@180s
Type "scd2/history.sh" Enter
Wait@90s
Sleep 8s

# beat: scd2-v3 | Batch 3: a typo fix and a dish off the menu
Hide
Type "clear" Enter
Show
Type "cat scd2/incoming/batch-3.json" Enter
Sleep 3s
Type "scd2/publish.sh scd2/incoming/batch-3.json && scd2/run.sh" Enter
Wait@180s
Type "scd2/history.sh" Enter
Wait@90s
Sleep 9s
