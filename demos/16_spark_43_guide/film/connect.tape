# The Ultimate Guide to Apache Spark 4.3: Spark Connect. Storyboard: storyboard.md.
#   film render demos/16_spark_43_guide/film/connect.tape --format square
Set TypingSpeed 40ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip.
Hide
Type "cd $FILM_DEMO && export VIRTUAL_ENV_DISABLE_PROMPT=1 FILM_RUN_QUIET=1 FILM_RUN_PYTHON=.venv/bin/python SPARK_LOCAL_IP=127.0.0.1 && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua' && alias python=.venv/bin/python" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}%1~%f %F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: connect-client | Operation IDs from the client
Hide
Type "clear; bin/connect-server.sh start; rm -f data/failed_op; clear" Enter
Wait@120s
Type "export FILM_RUN_HEIGHT=6" Enter
Type "nvim +/'with remote' connect_ops.py" Enter
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

# beat: connect-rest | The same operation, from the server's REST API
Hide
Type "export API=localhost:4043/api/v1/applications/$(curl -s localhost:4043/api/v1/applications | jq -r '.[0].id') OP=$(cat data/failed_op); clear" Enter
Sleep 1s
Show
Type "# new in 4.3: Connect sessions and operations in the REST API" Enter
Sleep 500ms
Type "curl -s $API/connect/sessions | jq" Enter
Sleep 4s
Type "# the failed operation, looked up by the ID the client printed" Enter
Sleep 500ms
Type "curl -s $API/connect/operations | jq '.[] | select(.operationId == env.OP) | {operationId, state, detail}'" Enter
Sleep 9s
