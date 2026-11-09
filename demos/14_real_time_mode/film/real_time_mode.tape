# Real-time Mode on Spark 4.3, the companion to "Getting Started with Real-time Mode on Spark".
# Storyboard: storyboard.md.
#   film render demos/14_real_time_mode/film/real_time_mode.tape [--format vertical]
# Needs Kafka up (docker compose up -d --wait), .venv synced, data/catalog built and the
# Scala jar built. Every run is real; the long waits are cut with Hide.
Set TypingSpeed 40ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 FILM_RUN_PYTHON=.venv/bin/python && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua' && alias python=.venv/bin/python" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}%1~%f %F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: basics | Step 1: a stream is a table that keeps growing
Hide
Type "rm -rf data/checkpoints/01-basics; export RUN_SECONDS=24; (python bin/shoppers.py --reset --rate 40 --seconds 50 --quiet >/dev/null 2>&1 &); sleep 6; clear" Enter
Sleep 7s
Type "nvim +/'trigger(processingTime' 01_streaming_basics.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "zb"
Show
Sleep 6s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@90s /Process exited/
Sleep 6s
Hide
Type ":qa!" Enter
Sleep 4s

# beat: trigger | Step 2: Real-time Mode is a trigger
Hide
Type "clear" Enter
Type "nvim +/'if a.mode' 02_real_time_enrich.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "zz"
Show
Sleep 9s
Hide
Type ":qa!" Enter
Sleep 500ms
Type "clear" Enter
Sleep 300ms
Show
Type "# the same query, measured in micro-batch and then Real-time" Enter
Sleep 600ms
Type "bin/measure.sh 02_real_time_enrich.py micro enriched 200 20" Enter
Hide
Wait@180s
Show
Sleep 2s
Type "bin/measure.sh 02_real_time_enrich.py rtm enriched 200 20" Enter
Hide
Wait@180s
Show
Sleep 7s

# beat: stateful | Step 3: stateful queries through the pipelined shuffle
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
Type "# dedup + a windowed count in Real-time Mode, then with the shuffle flush wait at 1 ms" Enter
Sleep 600ms
Type "bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 2s
Type "SHUFFLE_WAIT_MS=1 bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 7s

# beat: processor | Step 4: a taste vector per shopper
Hide
Type "clear" Enter
Type "nvim +/'override def handleInputRows' scala/src/main/scala/bookshop/Recommender.scala" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "zt"
Show
Sleep 21s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: live | Picks on every click
Hide
Type "clear; rm -f data/logs/04_recs-rtm-demo.log; (bin/demo_recs.sh rtm 45 100 > data/logs/film-recs.log 2>&1 &); until grep -q '^running' data/logs/04_recs-rtm-demo.log 2>/dev/null; do sleep 1; done; sleep 9; clear" Enter
Wait@180s
Show
Type "# follow one shopper: each click, and the picks Spark sends back" Enter
Sleep 600ms
Type "python bin/watch.py --seconds 22" Enter
Wait@60s
Sleep 3s

# beat: grade | Does it personalise?
Hide
Type "until grep -q 'nudges:' data/logs/film-recs.log; do sleep 2; done; clear" Enter
Wait@240s
Show
Type "# graded against each shopper's hidden favourite aisles" Enter
Sleep 600ms
Type "python bin/grade.py" Enter
Wait@60s
Sleep 18s
