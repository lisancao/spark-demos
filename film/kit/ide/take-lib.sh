# Helpers for an IDE take on the film display (:99). Source from a take script after
# setting `here` (the film folder) and `mode` (record | dry | prep).
#   record  ffmpeg records renders/take-raw.mp4; `beat` logs renders/take.marks
#   dry     no recording; `beat` screenshots renders/dry-NN-<id>.png as each beat starts
#   prep    the take script runs its off-camera reset and exits
# Finish a recorded take with: film.py ide <film folder>
export DISPLAY=:99
mkdir -p "$here/renders"
_n=0
_t0=

beat() { # beat <id>: a beat starts here (ids match storyboard.md)
  _n=$((_n + 1))
  case "$mode" in
    record) printf '%s\t%s\n' "$1" "$(awk -v a="$_t0" -v b="$(date +%s.%N)" 'BEGIN{printf "%.2f", b-a}')" >>"$here/renders/take.marks" ;;
    dry) import -window root -resize 1600x "$here/renders/dry-$(printf %02d $_n)-$1.png" ;;
  esac
}
hold() { sleep "$1"; }
keys() { xdotool type --delay 120 "$1"; sleep 0.15; } # IdeaVim drops keys typed faster
glide() { # glide x y: ease the pointer over ~0.6s, so clicks are seen arriving
  eval "$(xdotool getmouselocation --shell)"
  local x0=$X y0=$Y i t
  for i in $(seq 1 18); do
    t=$(awk -v i="$i" 'BEGIN{t=i/18; printf "%.4f", t*t*(3-2*t)}')
    xdotool mousemove "$(awk -v a="$x0" -v b="$1" -v t="$t" 'BEGIN{printf "%d", a+(b-a)*t}')" \
                      "$(awk -v a="$y0" -v b="$2" -v t="$t" 'BEGIN{printf "%d", a+(b-a)*t}')"
    sleep 0.033
  done
}
vimaction() { # vimaction <ActionId>...: run IDE actions by exact id through IdeaVim (editor focused)
  # Not Ctrl+Shift+A: its search ranks Settings pages above actions on a fresh
  # profile, so a typed name can open Settings instead. Ids: `:actionlist <word>`.
  local id
  for id in "$@"; do
    xdotool key Escape; sleep 0.3
    xdotool type --delay 40 ":action $id"; xdotool key Return; sleep 1
  done
}
wait_window() { # wait_window <title part>: the window appears after ~40s, and the
  # IDE ignores keys for a while longer while it indexes
  local i
  for i in $(seq 1 90); do xdotool search --onlyvisible --name "$1" >/dev/null 2>&1 && break; sleep 2; done
  sleep 35
}
start_recording() {
  [[ "$mode" == record ]] || return 0
  : >"$here/renders/take.marks"
  ffmpeg -y -v error -f x11grab -draw_mouse 1 -framerate 30 -video_size 2560x1440 -i :99 \
    -c:v libx264 -preset veryfast -crf 16 -pix_fmt yuv420p "$here/renders/take-raw.mp4" &
  _ff=$!
  _t0=$(date +%s.%N)
  # ffmpeg exits 255 on SIGINT, which is how it is stopped; that is not a failed take.
  trap 'kill -INT $_ff 2>/dev/null; wait $_ff 2>/dev/null || true' EXIT
  sleep 1
}
