#!/usr/bin/env bash
# Runs the demo against a Spark Connect server and fails if any cross-check prints FAIL.
# Usage: SPARK_REMOTE=sc://localhost:15002 ./verify.sh
set -euo pipefail
cd "$(dirname "$0")"
cargo build --release --quiet
out=$(SPARK_REMOTE="${SPARK_REMOTE:-sc://localhost:15002}" ./target/release/arrow_handoff 2>&1)
printf '%s\n' "$out"
pass=$(grep -c '^  PASS' <<<"$out" || true)
fail=$(grep -c '^  FAIL' <<<"$out" || true)
echo
echo "checks: $pass PASS, $fail FAIL"
[ "$fail" -eq 0 ] && [ "$pass" -ge 7 ]
