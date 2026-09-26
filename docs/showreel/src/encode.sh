#!/usr/bin/env bash
# Turns rendered frames + the synthesized soundtrack into the two published files:
#   docs/showreel/showreel.mp4   1920x1080, 60 fps, H.264 + AAC (the full-quality reel)
#   docs/showreel/showreel.webp  960x540, 25 fps, looping, silent (the README hero: GitHub only
#                                plays uploaded videos inline, and a GIF of this reel weighs 60 MB)
#
#   node docs/showreel/src/render.mjs --out /tmp/frames
#   docs/showreel/src/encode.sh /tmp/frames
#
# Needs ffmpeg with libx264 (set FFMPEG=/path/to/ffmpeg if it isn't on PATH) and python3 with numpy + scipy.
set -euo pipefail
FRAMES=${1:?usage: encode.sh <frames dir>}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$(cd "$HERE/.." && pwd)
FFMPEG=${FFMPEG:-ffmpeg}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

python3 "$HERE/soundtrack.py" "$TMP/soundtrack.wav"

# MP4: BT.709 conversion so colours match the canvas; faststart so it streams
"$FFMPEG" -y -loglevel error -framerate 60 -i "$FRAMES/f_%05d.png" -i "$TMP/soundtrack.wav" \
  -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -c:v libx264 -preset slow -crf 20 -tune animation -profile:v high -level 4.2 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 192k -shortest -movflags +faststart "$OUT/showreel.mp4"

# Animated WebP: full colour at a fraction of a GIF's size, plays in every current browser
"$FFMPEG" -y -loglevel error -framerate 60 -i "$FRAMES/f_%05d.png" \
  -vf "fps=25,scale=960:540:flags=lanczos" \
  -c:v libwebp_anim -quality 80 -compression_level 3 -loop 0 "$OUT/showreel.webp"

ls -lh "$OUT/showreel.mp4" "$OUT/showreel.webp"
