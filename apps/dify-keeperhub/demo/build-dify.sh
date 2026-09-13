#!/usr/bin/env bash
# Assemble the silent, caption-driven demo. No VO track by design: every
# claim has to be readable on screen, so captions are burned as PIL plates
# (this ffmpeg has no libass).
set -euo pipefail
W=work-dify; mkdir -p $W; rm -f $W/*.mp4 $W/list.txt
FPS=30

# card <name> <image> <dur>  — a full-frame card, static
card () {
  local n=$1 img=$2 dur=$3
  ffmpeg -y -v error -loop 1 -i "$img" -t "$dur" \
    -vf "scale=1920:1080,format=yuv420p" -r $FPS -c:v libx264 -preset slow -crf 18 "$W/$n.mp4"
  echo "file '$PWD/$W/$n.mp4'" >> $W/list.txt; printf '  ✓ %-11s %ss\n' "$n" "$dur"
}

# shot <name> <frame> <dur> <crop> <caption>  — screen capture + caption plate
shot () {
  local n=$1 img=$2 dur=$3 crop=$4 cap=$5
  local frames; frames=$(python3 -c "print(int($dur*$FPS))")
  ffmpeg -y -v error -loop 1 -i "frames-dify/$img.png" -loop 1 -i "cards/$cap.png" -t "$dur" \
    -filter_complex "[0:v]${crop},scale=1920:1080:flags=lanczos,zoompan=z='min(zoom+0.00022,1.028)':d=${frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=${FPS}[bg];[bg][1:v]overlay=x=(W-w)/2:y=H-h-64:format=auto,format=yuv420p[v]" \
    -map "[v]" -r $FPS -c:v libx264 -preset slow -crf 18 "$W/$n.mp4"
  echo "file '$PWD/$W/$n.mp4'" >> $W/list.txt; printf '  ✓ %-11s %ss  %s\n' "$n" "$dur" "$img"
}

echo "rendering…"
card s1 cards/c1-title.png            7
shot s2 d1-canvas   10 "crop=1250:703:520:653"   cap-canvas
shot s3 d4-tracing   9 "crop=1560:878:1640:55"   cap-tracing
shot s4 d3-detail   12 "crop=1340:754:1860:55"   cap-result
shot s5 d5-detail    8 "crop=1180:664:2020:95"   cap-detail
card s6 cards/c6-guard.png           13
shot s7 e1-explorer 12 "crop=2800:1575:100:425"  cap-explorer
card s8 cards/c8-close.png            7

echo "concatenating…"
ffmpeg -y -v error -f concat -safe 0 -i $W/list.txt -c copy "$W/silent.mp4"
# a silent track keeps players and uploaders from choking on a video-only file
ffmpeg -y -v error -i "$W/silent.mp4" -f lavfi -i anullsrc=r=48000:cl=stereo \
  -shortest -c:v copy -c:a aac -b:a 96k -movflags +faststart \
  "$HOME/Downloads/kajota-dify-keeperhub-demo.mp4"
ffprobe -v error -show_entries format=duration,size -show_entries stream=width,height,codec_name \
  -of default=noprint_wrappers=1 "$HOME/Downloads/kajota-dify-keeperhub-demo.mp4"
