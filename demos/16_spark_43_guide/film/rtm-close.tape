# The Ultimate Guide to Apache Spark 4.3: Real-time Mode, square piece, shot 3 of 4.
# The same file at a large font for a phone: move through it, highlighting the block that
# matters at each step; rtm-run.tape runs it. The piece's caption bar (under the film)
# says what each highlight is; the film itself carries no captions.
#   film render demos/16_spark_43_guide/film/rtm-close.tape --format square --demo demos/14_real_time_mode
# Needs, in demo 14: Kafka up (docker compose up -d --wait), .venv synced, data/catalog built,
# and nothing else using the cores.
Set Height 900
Set FontSize 30
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

# beat: rtm-code | Read, dedup, count, and the one Real-time line
# The view scrolls a line at a time (Ctrl+E) so each highlighted block sits high on the
# screen; the cursor is put on the block while hidden.
Hide
Type "clear" Enter
Type "nvim +22 03_stateful_trending.py" Enter
Sleep 2.5s
Type ":noh | hi FilmHi guibg=#5a2c12 | let g:ns = nvim_create_namespace('film') | set scrolloff=0" Enter
Type "20Gzt22G"
Type ":echo ''" Enter
Ctrl+L
Show
Sleep 1.2s
Hide
Type ":for l in range(21, 28) | call nvim_buf_set_extmark(0, g:ns, l, 0, {'line_hl_group': 'FilmHi'}) | endfor | echo ''" Enter
Show
Sleep 4.5s
Hide
Type ":call nvim_buf_clear_namespace(0, g:ns, 0, -1) | echo ''" Enter
Show
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Hide
Type "32G"
Type ":call nvim_buf_set_extmark(0, g:ns, 31, 0, {'line_hl_group': 'FilmHi'}) | echo ''" Enter
Show
Sleep 5s
Hide
Type ":call nvim_buf_clear_namespace(0, g:ns, 0, -1) | for l in range(34, 37) | call nvim_buf_set_extmark(0, g:ns, l, 0, {'line_hl_group': 'FilmHi'}) | endfor | echo ''" Enter
Type "35G"
Show
Sleep 5.5s
Hide
Type ":call nvim_buf_clear_namespace(0, g:ns, 0, -1) | echo ''" Enter
Show
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Ctrl+E
Sleep 120ms
Hide
Type "50G"
Type ":for l in [48, 49] | call nvim_buf_set_extmark(0, g:ns, l, 0, {'line_hl_group': 'FilmHi'}) | endfor | echo ''" Enter
Show
Sleep 6s
