#!/usr/bin/env bash
# Film helper for :Run (FILM_RUN_PYTHON=film/run-step.sh): runs the whole demo against the
# Connect server and prints only the steps a beat is about. The first argument is the file
# nvim passes and is ignored.
#   run-step.sh <file> 3        step 3
#   run-step.sh <file> 5 6      steps 5 to 6
#   run-step.sh <file> checks   every PASS/FAIL line and the timings
set -euo pipefail
shift
bin=${ARROW_HANDOFF_BIN:-./target/release/arrow_handoff}
if [[ ${1:-} == checks ]]; then
  "$bin" | grep -E '^  (PASS|FAIL)|^\| (step|[A-Z])|^\|---\|---\|$' | grep -v '^| Spark type'
  exit
fi
from=$1 to=${2:-$1}
# awk stops reading after the last step it prints, so the beat doesn't wait for the rest of
# the run; the demo then exits on the closed pipe, and its stderr (that panic) is dropped.
"$bin" 2>/dev/null | awk -W interactive -v from="$from" -v to="$to" '
  /^== [0-9]+\./ { n = $2 + 0; if (n > to) exit; on = (n >= from) }
  /^== Timings/  { exit }
  on' || true  # the demo exits 101 on the closed pipe
