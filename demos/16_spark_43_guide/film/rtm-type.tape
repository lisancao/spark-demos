# The Ultimate Guide to Apache Spark 4.3: Real-time Mode, square piece, shot 1 of 4.
# A normal terminal at the large font, the editor command typed; the cut lands on
# rtm-wide.tape's whole-file shot. 1080x900: the piece puts its
# caption bar under the film.
#   film render demos/16_spark_43_guide/film/rtm-type.tape --format square --demo demos/14_real_time_mode
Set Height 900
Set FontSize 30
Set Padding 24
Set TypingSpeed 60ms

Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua'" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: rtm-type | A terminal: open the query
Sleep 1.2s
Type "nvim 03_stateful_trending.py"
Sleep 500ms
