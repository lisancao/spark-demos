# Spark Connect from Rust, into DuckDB 2.0 and Polars: the companion to the post
# "Spark Connect from Rust: Pull Spark outputs into DuckDB and Polars".
# Storyboard: storyboard.md.
#   film render demos/09_spark_connect_rust/film/spark_connect_rust.tape [--format vertical]
#   film real   demos/09_spark_connect_rust/film/spark_connect_rust.tape
# Needs the demo's server (docker compose up -d --wait) and a release build in target/.
Set TypingSpeed 45ms
Set WaitPattern /❯$/

# Setup, off camera at the start of every clip: the demo folder, the server address, comments
# allowed, the film nvim config, and :Run pointed at run-step.sh (the whole program, printing
# only the beat's steps). cargo, and protoc if the build used a non-default one, come from the
# environment `film` runs in, so verify.sh's cargo build finds nothing to rebuild.
# The short prompt is for VHS; the real pass keeps hers.
Hide
Type "cd $FILM_DEMO && export SPARK_REMOTE=sc://localhost:15002 FILM_RUN_PYTHON=film/run-step.sh FILM_RUN_WIDTH=80 && setopt interactivecomments && alias nvim='nvim -u $FILM_KIT/nvim-film.lua'" Enter
Type "[[ -n $FILM_REAL ]] || PROMPT='%F{cyan}09_spark_connect_rust%f %F{magenta}❯%f '; clear" Enter
Sleep 1s
Show

# beat: open | Spark Connect from Rust, live
Sleep 800ms
Type "# Spark Connect from Rust: Spark 4.2.0 -> DuckDB 2.0 and polars 0.55. Every run is live." Enter
Sleep 16s

# beat: deps | The Cargo.toml
Hide
Ctrl+L
Show
Sleep 600ms
Type "# The Cargo.toml: the client (arrow 58 inside), arrow 60 for DuckDB 2.0, polars 0.55" Enter
Sleep 800ms
Type "nvim Cargo.toml"
Sleep 300ms
Enter
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "7G"
Type "zt"
Sleep 400ms
Show
Sleep 17s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: data | Step 1: data in Spark
Hide
Ctrl+L
Show
Sleep 600ms
Type "# Step 1: Spark builds 20M orders from range(), server side" Enter
Sleep 800ms
Type "nvim src/main.rs"
Sleep 300ms
Enter
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "61G"
Type "zt"
Sleep 400ms
Show
Sleep 4s
Type ":Run 1"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 9s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: arrow | Step 2: the result as Arrow
Hide
Ctrl+L
Show
Sleep 600ms
Type "# Step 2: one city's orders as Arrow batches, an Arrow IPC file, and Rows" Enter
Sleep 800ms
Type "nvim src/main.rs"
Sleep 300ms
Enter
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "84G"
Type "zt"
Sleep 400ms
Show
Sleep 6s
Type ":Run 2"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 10s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: duckdb | Step 3: DuckDB 2.0
Hide
Ctrl+L
Show
Sleep 600ms
Type "# Step 3: DuckDB 2.0 reads the IPC bytes and runs an ASOF JOIN" Enter
Sleep 800ms
Type "nvim src/main.rs"
Sleep 300ms
Enter
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "120G"
Type "zt"
Sleep 400ms
Show
Sleep 6s
Type ":Run 3"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 10s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: polars | Step 4: Polars
Hide
Ctrl+L
Show
Sleep 600ms
Type "# Step 4: Spark does the group-by, Polars the rolling window" Enter
Sleep 800ms
Type "nvim src/main.rs"
Sleep 300ms
Enter
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "199G"
Type "zt"
Sleep 400ms
Show
Sleep 4s
Type ":Run 4"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 9s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: back | Steps 5 and 6: Polars to DuckDB, DuckDB to Spark
Hide
Ctrl+L
Show
Sleep 600ms
Type "# Steps 5 and 6: Polars -> DuckDB as IPC, then DuckDB's rollup back to Spark" Enter
Sleep 800ms
Type "nvim src/main.rs"
Sleep 300ms
Enter
Hide
Sleep 2.5s
Type ":set so=0 | echo" Enter
Type "232G"
Type "zt"
Sleep 400ms
Show
Sleep 4s
Type ":Run 5 6"
Sleep 400ms
Enter
Wait+Screen@120s /Process exited/
Sleep 9s
Hide
Type ":qa!" Enter
Sleep 500ms

# beat: checks | verify.sh
Hide
Ctrl+L
Show
Sleep 600ms
Type "# Every hop checked against Spark, and every step timed" Enter
Sleep 800ms
Type "./verify.sh"
Sleep 300ms
Enter
Wait@180s
Sleep 14s
