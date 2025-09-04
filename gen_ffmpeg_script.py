#!/usr/bin/env python3
import argparse
import sys
import re
import os


def parse_filename(filepath):
    """
    Parse filename like IMG_20250728_115906_AATP1401.jpg
    Returns dict with date, time, and sequence number (AATP prefix removed)
    """
    filename = os.path.basename(filepath)
    # Match pattern: IMG_YYYYMMDD_HHMMSS_AATPNNNN.jpg and extract just the number part
    match = re.match(r"IMG_(\d{8})_(\d{6})_AATP(\d+)\.jpg$", filename)
    if match:
        date_str, time_str, sequence_str = match.groups()
        return {
            "date": date_str,
            "time": time_str,
            "sequence": int(
                sequence_str
            ),  # This removes AATP prefix, just stores the number
            "timestamp": (date_str, time_str, sequence_str),
            "filepath": filepath,
        }
    return None


def needs_quotes(path):
    """Check if path needs quotes (has spaces or special characters)"""
    # Don't quote command substitutions
    if path.startswith("$(") and path.endswith(")"):
        return False
    # Check for spaces, special shell characters, etc.
    special_chars = r'[ \t\n\r\f\v$`"\'\\;|&<>(){}*?[\]~#!]'
    return bool(re.search(special_chars, path))


def format_path(path):
    """Format path with quotes only if needed"""
    if needs_quotes(path):
        return f"'{path}'"
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Generate ffmpeg bash script from sorted image files"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="run_ffmpeg.sh",
        help="Output bash script (default: run_ffmpeg.sh)",
    )
    parser.add_argument(
        "-s",
        "--sort-by",
        choices=["timestamp", "sequence"],
        default="sequence",
        help="Sort by sequence (AATP number) or timestamp (date/time) (default: sequence)",
    )

    args = parser.parse_args()

    # Read file paths from stdin
    jpg_files = []
    mount_paths = set()

    for line in sys.stdin:
        filepath = line.strip()
        if not filepath:
            continue

        parsed = parse_filename(filepath)
        if parsed:
            if args.sort_by == "sequence":
                sort_key = parsed["sequence"]
            else:  # sort by timestamp
                sort_key = parsed["timestamp"]
            jpg_files.append(
                (sort_key, parsed["filepath"], os.path.basename(parsed["filepath"]))
            )
            # Track unique directory paths for mounting
            mount_paths.add(os.path.dirname(filepath))

    if not jpg_files:
        print("No matching image files found in input", file=sys.stderr)
        return 1

    # Sort by the chosen method
    jpg_files.sort(key=lambda x: x[0])

    # Create manifest content
    manifest_content = []
    for sort_key, full_path, filename in jpg_files:
        # Use /input prefix for docker paths
        docker_path = f"/input/{filename}"
        manifest_content.append(f"file {format_path(docker_path)}\n")

    # Generate bash script
    with open(args.output, "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Generated ffmpeg script\n\n")

        # Create manifest file
        f.write("# Create manifest file\n")
        f.write("cat > ffmpeg_list.txt << 'EOF'\n")
        for line in manifest_content:
            f.write(line)
        f.write("EOF\n\n")

        # Docker command with proper volume mounts
        f.write("# Run ffmpeg in docker\n")
        f.write("docker run --rm --name wackywolffish \\\n")
        f.write(f"-v {format_path('$(pwd)')}:/workspace \\\n")

        # Mount each unique directory
        for mount_path in sorted(mount_paths):
            f.write(f"-v {format_path(mount_path)}:/input \\\n")

        f.write("jrottenberg/ffmpeg:latest \\\n")
        f.write("-y \\\n")
        f.write("-f concat \\\n")
        f.write("-safe 0 \\\n")
        f.write("-i /workspace/ffmpeg_list.txt \\\n")
        f.write("-r 15 \\\n")
        f.write("-vf scale=1280:720 \\\n")
        f.write("-c:v libx264 \\\n")
        f.write("-preset fast \\\n")
        f.write("-crf 28 \\\n")
        f.write("-pix_fmt yuv420p \\\n")
        f.write("/workspace/timelapse.mp4\n")

    # Make the script executable
    os.chmod(args.output, 0o755)

    sort_method = "sequence number" if args.sort_by == "sequence" else "timestamp"
    print(
        f"Generated {args.output} with {len(jpg_files)} files sorted by {sort_method}",
        file=sys.stderr,
    )
    print(f"Files sorted from {jpg_files[0][2]} to {jpg_files[-1][2]}", file=sys.stderr)


if __name__ == "__main__":
    main()
