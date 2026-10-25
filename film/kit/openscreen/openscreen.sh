#!/usr/bin/env bash
# Export a .openscreen project (from `film.py zoom`, or edited by hand) through OpenScreen
# itself, on a hidden display, so its backdrop, shadow, corners and motion blur render.
#   openscreen.sh <project.openscreen> <out.mp4>
# OpenScreen 1.5 runs from its AppImage (OPENSCREEN_APPIMAGE), unpacked once into
# ~/.cache/film-kit. It gets a private session bus, so its file dialogs are GTK ones on
# the hidden display and never the desktop portal on Lisa's screen, and Vulkan ANGLE,
# because without a GPU it renders about one frame a second.
set -euo pipefail
project=$(realpath "$1")
out=$(realpath -m "$2")
here=$(cd "$(dirname "$0")" && pwd)
appimage=${OPENSCREEN_APPIMAGE:-$HOME/Downloads/Openscreen-Linux-1.5.0.AppImage}
app=$HOME/.cache/film-kit/openscreen-1.5.0
display=${FILM_OS_DISPLAY:-:97}
port=${FILM_OS_PORT:-9431}
work=$(mktemp -d)

if [[ ! -x $app/openscreen ]]; then
  mkdir -p "$(dirname "$app")"
  (cd "$work" && "$appimage" --appimage-extract >/dev/null)
  mv "$work/squashfs-root" "$app"
fi
if ss -ltn | grep -q ":$port "; then
  echo "port $port is taken; set FILM_OS_PORT" >&2
  exit 1
fi
rm -f "$out"

pids=()
cleanup() {
  for p in "${pids[@]}"; do kill "$p" 2>/dev/null || true; done
  wait 2>/dev/null || true
  rm -rf "$work"
}
trap cleanup EXIT

Xvfb "$display" -screen 0 2560x1440x24 >/dev/null 2>&1 &
pids+=($!)
sleep 1
DISPLAY=$display openbox >/dev/null 2>&1 &
pids+=($!)
DISPLAY=$display GTK_USE_PORTAL=0 dbus-run-session -- "$app/openscreen" --no-sandbox \
  --user-data-dir="$work/profile" --remote-debugging-port="$port" --ignore-gpu-blocklist \
  --use-angle=vulkan --enable-features=Vulkan,VulkanFromANGLE,DefaultANGLEVulkan \
  >"$work/app.log" 2>&1 &
pids+=($!)
sleep 8
DISPLAY=$display node "$here/export.mjs" "$port" "$project" "$out"
