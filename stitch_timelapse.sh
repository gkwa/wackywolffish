#!/bin/bash
# Simple timelapse video creation script using Docker
# Usage: ./stitch_timelapse.sh <manifest_file>

if [ $# -ne 1 ]; then
    echo "Usage: $0 <manifest_file>"
    exit 1
fi

MANIFEST_FILE="$1"

# Check if manifest file exists
if [ ! -f "$MANIFEST_FILE" ]; then
    echo "Error: Manifest file $MANIFEST_FILE not found."
    exit 1
fi

# Use Docker ffmpeg with concat method
docker run --rm --name wackywolffish \
    -v "$(pwd)":/workspace \
    -v ~/Root:/root_mount:ro \
    jrottenberg/ffmpeg:latest \
    -y \
    -f concat \
    -safe 0 \
    -i "/workspace/$(basename "$MANIFEST_FILE")" \
    -r 15 \
    -vf "scale=1280:720" \
    -c:v libx264 \
    -preset fast \
    -crf 28 \
    -pix_fmt yuv420p \
    "/workspace/timelapse.mp4"
