# The Ultimate Guide to Apache Spark 4.3: stateful Real-time Mode. Storyboard: storyboard.md.
# Films demo 14 (Real-time Mode) in square:
#   film render demos/16_spark_43_guide/film/rtm.tape --format square --demo demos/14_real_time_mode
# Needs, in demo 14: Kafka up (docker compose up -d --wait), .venv synced, data/catalog built,
# the Scala jar built, and nothing else using the cores. Beats copied from its own tape.
Set TypingSpeed 40ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 FILM_RUN_PYTHON=.venv/bin/python SPARK_LOCAL_IP=127.0.0.1 && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua' && alias python=.venv/bin/python" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}%1~%f %F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: rtm-stateful | Stateful queries through the pipelined shuffle
Hide
Type "clear" Enter
Type "nvim +/'^trending = ' 03_stateful_trending.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "zt"
Show
Sleep 10s
Hide
Type ":qa!" Enter
Sleep 500ms
Type "clear" Enter
Sleep 300ms
Show
Type "# dedup + windowed count in Real-time Mode" Enter
Sleep 600ms
Type "bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 2s
Type "# again, with the shuffle flush wait at 1 ms" Enter
Sleep 600ms
Type "SHUFFLE_WAIT_MS=1 bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 8s

# beat: rtm-live | Picks on every click, from transformWithState
Hide
Type "clear; rm -f data/logs/04_recs-rtm-demo.log; (bin/demo_recs.sh rtm 45 100 > data/logs/film-recs.log 2>&1 &); until grep -q '^running' data/logs/04_recs-rtm-demo.log 2>/dev/null; do sleep 1; done; sleep 9; clear" Enter
Wait@180s
Show
Type "# one shopper: each click, and the picks Spark sends back" Enter
Sleep 600ms
Type "python bin/watch.py --seconds 22" Enter
Wait@60s
Sleep 3s
Hide
Type "until grep -q 'nudges:' data/logs/film-recs.log; do sleep 2; done; clear" Enter
Wait@240s
