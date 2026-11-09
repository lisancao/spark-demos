#!/usr/bin/env bash
# Per-feature square clips -> MP4 + 720px 10 fps GIF named for the post.
#   film/make-gifs.sh <out-dir> [clip ...]   (default: every clip in renders/square)
set -euo pipefail
out=$1; shift
cd "$(dirname "$0")/renders/square"
clips=("$@"); [[ ${#clips[@]} -gt 0 ]] || clips=(*.mp4)
for c in "${clips[@]}"; do
  id=${c#[0-9][0-9]-}; id=${id%.mp4}
  cp "$c" "$out/spark-4-3-guide-$id.mp4"
  ffmpeg -v error -y -i "$c" -vf "fps=10,scale=720:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96[p];[b][p]paletteuse=dither=none" \
    "$out/spark-4-3-guide-$id.gif"
done
