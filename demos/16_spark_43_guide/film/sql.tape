# The Ultimate Guide to Apache Spark 4.3: Spark SQL. Storyboard: storyboard.md.
#   film render demos/16_spark_43_guide/film/sql.tape --format square
Set TypingSpeed 40ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 FILM_RUN_PYTHON=.venv/bin/python SPARK_LOCAL_IP=127.0.0.1 PYSPARK_PYTHON=$PWD/.venv/bin/python SPARK_CONF_DIR=$PWD/conf && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua' && alias python=.venv/bin/python" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}%1~%f %F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: asof | ASOF JOIN
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=9" Enter
Type "nvim +/'ASOF JOIN' asof_join.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "gg"
Show
Sleep 6s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 6s
Hide
Type ":qa!" Enter
Sleep 1s

# beat: json-table | JSON_TABLE
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=9" Enter
Type "nvim +/'JSON_TABLE' json_table.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "gg"
Show
Sleep 4s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 5s
Hide
Type ":qa!" Enter
Sleep 1s

# beat: variant | VARIANT edits
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=6" Enter
Type "nvim +/'edits =' variant_edit.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "gg"
Show
Sleep 4s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 5s
Hide
Type ":qa!" Enter
Sleep 1s

# beat: nanos | Nanosecond timestamps
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=15" Enter
Type "nvim +/'TIMESTAMP_NTZ(9)' nanos.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "gg"
Show
Sleep 5s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 6s
Hide
Type ":qa!" Enter
Sleep 1s

# beat: sql-extras | UNNEST, counter_diff, jaro_winkler_similarity
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=20" Enter
Type "nvim +/'UNNEST' sql_extras.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "gg"
Show
Sleep 5s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 7s
Hide
Type ":qa!" Enter
Sleep 1s

# beat: archives | Reading files inside archives
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=10" Enter
Type "nvim +/'archivePathFilter' archives.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "gg"
Show
Sleep 4s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 5s
Hide
Type ":qa!" Enter
Sleep 1s
