# The Ultimate Guide to Apache Spark 4.3: Real-time Mode, square piece, shot 4 of 4.
# The run, at the largest font the latency line fits: default flush wait, then 1 ms.
# The piece's caption bar says which is which; the numbers are this take's.
#   film render demos/16_spark_43_guide/film/rtm-run.tape --format square --demo demos/14_real_time_mode
# Needs, in demo 14: Kafka up (docker compose up -d --wait), .venv synced, data/catalog built,
# and nothing else using the cores.
Set Height 900
Set FontSize 36
Set Padding 24
Set TypingSpeed 40ms
Set WaitPattern /❯$/

Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 SPARK_LOCAL_IP=127.0.0.1 && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua'" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{magenta}❯%f '; clear" Enter
# phone width: start the latency figures on their own line (the output itself is unchanged)
Type 'function bin/measure.sh { command bin/measure.sh "$@" | sed -u "s/  p50/\n  p50/"; }; clear' Enter
Sleep 1s
Show

# beat: rtm-measure | Run it: default flush wait, then 1 ms
Hide
Type "clear" Enter
Sleep 300ms
Show
Sleep 500ms
Type "bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 5s
Type "SHUFFLE_WAIT_MS=1 bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 7s
