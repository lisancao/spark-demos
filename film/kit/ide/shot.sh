#!/usr/bin/env bash
# Screenshot the film display, scaled to 1600 wide: 1 px in the image = 1.6 px on :99.
out="${1:-/tmp/film-shot.png}"
DISPLAY=:99 import -window root -resize 1600x "$out" && echo "$out"
