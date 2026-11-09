# The Ultimate Guide to Apache Spark 4.3: PySpark. Storyboard: storyboard.md.
#   film render demos/16_spark_43_guide/film/pyspark.tape --format square
Set TypingSpeed 40ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 FILM_RUN_PYTHON=.venv/bin/python SPARK_LOCAL_IP=127.0.0.1 PYSPARK_PYTHON=$PWD/.venv/bin/python SPARK_CONF_DIR=$PWD/conf && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua' && alias python=.venv/bin/python" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}%1~%f %F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: zip | DataFrame.zip
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=11" Enter
Type "nvim +/'ids.zip' zip_frames.py" Enter
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

# beat: transpile | Python UDFs transpiled to Spark expressions
Hide
Type "clear" Enter
Type "export FILM_RUN_HEIGHT=13" Enter
Type "nvim +/'transpilePyUDFs' udf_transpile.py" Enter
Sleep 2.5s
Type ":noh" Enter
Ctrl+L
Type "gg"
Show
Sleep 7s
Type ":Run"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 8s
Hide
Type ":qa!" Enter
Sleep 1s
