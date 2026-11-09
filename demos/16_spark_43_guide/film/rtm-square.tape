# The Ultimate Guide to Apache Spark 4.3: stateful Real-time Mode, cut for a phone.
# Square, full frame, a bigger font than the square default, the lines that matter highlighted,
# then the run on its own screen. `film zoom` moves in on the highlights and the latency lines.
#   film render demos/16_spark_43_guide/film/rtm-square.tape --format square --demo demos/14_real_time_mode
#   film zoom demos/16_spark_43_guide/film/renders/rtm-square-square.mp4 --format square
# Needs, in demo 14: Kafka up (docker compose up -d --wait), .venv synced, data/catalog built,
# and nothing else using the cores.
Set FontSize 25
Set Padding 24
Set TypingSpeed 40ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 FILM_RUN_PYTHON=.venv/bin/python SPARK_LOCAL_IP=127.0.0.1 && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua' && alias python=.venv/bin/python" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}%1~%f %F{magenta}❯%f '; clear" Enter
# phone width: start the latency figures on their own line (the output itself is unchanged)
Type 'function bin/measure.sh { command bin/measure.sh "$@" | sed -u "s/  p50/\n  p50/"; }; clear' Enter
Sleep 1s
Show

# beat: rtm-code | The query: two stateful steps, one Real-time line
Hide
Type "clear" Enter
Type "nvim +31 03_stateful_trending.py" Enter
Sleep 2.5s
Type ":set nowrap | noh" Enter
Type ":hi FilmHi guibg=#4a2614 | let g:ns = nvim_create_namespace('film')" Enter
Type "zt"
Ctrl+L
Show
Sleep 3s
Hide
Type ":for l in [31, 34] | call nvim_buf_set_extmark(0, g:ns, l, 0, {'line_hl_group': 'FilmHi'}) | endfor" Enter
Type ":echo ''" Enter
Show
Sleep 7s
Hide
Type ":call nvim_buf_clear_namespace(0, g:ns, 0, -1) | for l in [48, 49] | call nvim_buf_set_extmark(0, g:ns, l, 0, {'line_hl_group': 'FilmHi'}) | endfor" Enter
Type ":echo ''" Enter
Show
Sleep 7s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: rtm-run | Measured end to end, then with the flush wait at 1 ms
Hide
Type "clear" Enter
Sleep 300ms
Show
Type "# dedup + windowed count, Real-time Mode" Enter
Sleep 600ms
Type "bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 6s
Type "# again, shuffle flush wait at 1 ms" Enter
Sleep 600ms
Type "SHUFFLE_WAIT_MS=1 bin/measure.sh 03_stateful_trending.py rtm trending 200 20" Enter
Hide
Wait@180s
Show
Sleep 8s
