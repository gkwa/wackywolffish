#!/bin/bash

# Simple timelapse video creation script using Docker
# Usage: ./stitch_timelapse.sh [max_minutes]
# Example: ./stitch_timelapse.sh 5  (process only first 5 minutes of images)
#
# Assumes images are taken every 30 seconds
#
# Different framerates for 1997 images:
# * 24 fps: 1997 ÷ 24 = 83 seconds (1 min 23 sec)
# * 15 fps: 1997 ÷ 15 = 133 seconds (2 min 13 sec)
# * 10 fps: 1997 ÷ 10 = 200 seconds (3 min 20 sec)
# * 5 fps: 1997 ÷ 5 = 399 seconds (6 min 39 sec)

INPUT_DIR="/Users/mtm/xs7j3-v79mm/AKASO GO"
OUTPUT_FILE="timelapse.mp4"
FRAMERATE=15
PROGRESS_FILE="ffmpeg_progress.log"

# Check if max_minutes parameter is provided
MAX_MINUTES=${1:-}
LIMIT_FRAMES=""

if [ -n "$MAX_MINUTES" ]; then
   # Calculate max frames: minutes * 60 seconds / 30 seconds per image
   MAX_FRAMES=$((MAX_MINUTES * 2))
   LIMIT_FRAMES="-frames:v $MAX_FRAMES"
   OUTPUT_FILE="preview.mp4"
   echo "Processing only first $MAX_MINUTES minutes ($MAX_FRAMES frames)"
else
   echo "Processing all images"
fi

echo "Creating timelapse video from images in: $INPUT_DIR"
echo "Output file: $OUTPUT_FILE"
echo "Frame rate: $FRAMERATE fps"
echo "Progress log: $PROGRESS_FILE"

# Use Docker ffmpeg to create video from image sequence
docker run --rm --name wackywolffish \
 -v "$INPUT_DIR":/input \
 -v "$(pwd)":/output \
 jrottenberg/ffmpeg:latest \
 -y \
 -progress pipe:1 \
 -pattern_type glob \
 -i "/input/IMG*.jpg" \
 $LIMIT_FRAMES \
 -r $FRAMERATE \
 -vf "scale=1280:720" \
 -c:v libx264 \
 -preset fast \
 -crf 28 \
 -pix_fmt yuv420p \
 "/output/$OUTPUT_FILE" | tee "$PROGRESS_FILE"

echo "Timelapse video created: $OUTPUT_FILE"
