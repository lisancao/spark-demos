# The Ultimate Guide to Apache Spark 4.3: Real-time Mode, square piece, shot 2 of 4.
# The whole query file at a small font, the establishing shot, after rtm-type.tape's
# typed command; rtm-close.tape picks up on the same file at a large font. 1080x900: the piece puts its
# caption bar under the film.
#   film render demos/16_spark_43_guide/film/rtm-wide.tape --format square --demo demos/14_real_time_mode
Set Height 900
Set FontSize 14
Set Padding 24
Set TypingSpeed 60ms

Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua'" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: rtm-open | The whole query
Hide
Type "nvim 03_stateful_trending.py" Enter
Sleep 2.5s
Type ":echo ''" Enter
Ctrl+L
Show
Sleep 3.2s
