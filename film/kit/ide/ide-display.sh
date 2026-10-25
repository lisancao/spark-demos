#!/usr/bin/env bash
# Start (or stop) the film display: Xvfb :99 at 2560x1440 with its own openbox, then
# IntelliJ on the film profile. Nothing appears on the real desktop.
#   ide-display.sh start <project-dir>   |   ide-display.sh stop
# Stop kills only the PIDs this script recorded: the real desktop also runs openbox.
set -euo pipefail
kit="$(cd "$(dirname "$0")" && pwd)"
F="${FILM_IDE_PROFILE:-$kit/profile}"
[[ -d "$F" ]] || { echo "no film profile; run make-profile.sh first" >&2; exit 1; }
D=:99
PIDS="$F/log/pids"
case "${1:-}" in
  start)
    : >"$PIDS"
    Xvfb $D -screen 0 2560x1440x24 -nolisten tcp >"$F/log/xvfb.out" 2>&1 & echo $! >>"$PIDS"
    sleep 1
    DISPLAY=$D openbox --config-file "$kit/openbox-film.xml" >"$F/log/openbox.out" 2>&1 & echo $! >>"$PIDS"
    sleep 1
    env -u WAYLAND_DISPLAY DISPLAY=$D IDEA_PROPERTIES="$F/idea.properties" IDEA_VM_OPTIONS="$F/idea64.vmoptions" \
      setsid /snap/intellij-idea-community/current/bin/idea.sh "$2" >"$F/log/idea.out" 2>&1 & echo $! >>"$PIDS"
    echo "started on $D: $(tr '\n' ' ' <"$PIDS")"
    ;;
  stop)
    # IntelliJ first (its whole session), then openbox and Xvfb, newest first.
    tac "$PIDS" 2>/dev/null | while read -r pid; do
      pkill -TERM -s "$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
      sleep 2
    done
    : >"$PIDS"
    ;;
  *) echo "usage: $0 start <project-dir> | stop" >&2; exit 2 ;;
esac
