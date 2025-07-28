#!/bin/bash

# Simple timelapse video creation script using Docker
# Usage: ./stitch_timelapse.sh
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

echo "Creating timelapse video from images in: $INPUT_DIR"
echo "Output file: $OUTPUT_FILE"
echo "Frame rate: $FRAMERATE fps"

# Use Docker ffmpeg to create video from image sequence
docker run --rm \
    -v "$INPUT_DIR":/input \
    -v "$(pwd)":/output \
    jrottenberg/ffmpeg:latest \
    -y \
    -pattern_type glob \
    -i "/input/IMG*.jpg" \
    -r $FRAMERATE \
    -c:v libx264 \
    -pix_fmt yuv420p \
    -crf 23 \
    "/output/$OUTPUT_FILE"

echo "Timelapse video created: $OUTPUT_FILE"
