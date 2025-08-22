#!/usr/bin/env python3

import argparse
import os
import re


def parse_filename(filename):
    """
    Parse filename like IMG_20250728_115906_AATP1401.jpg
    Returns dict with date, time, and sequence number (AATP prefix removed)
    """
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
        }
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Sort image files by timestamp or sequence and output in ffmpeg list format"
    )
    parser.add_argument("directory", help="Directory containing image files")
    parser.add_argument(
        "-o",
        "--output",
        default="ffmpeg_list.txt",
        help="Output file (default: ffmpeg_list.txt)",
    )
    parser.add_argument(
        "-s",
        "--sort-by",
        choices=["timestamp", "sequence"],
        default="sequence",
        help="Sort by sequence (AATP number) or timestamp (date/time) (default: sequence)",
    )

    args = parser.parse_args()

    # Check if directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory '{args.directory}' does not exist")
        return 1

    # Get all .jpg files in directory
    jpg_files = []
    for file in os.listdir(args.directory):
        if file.lower().endswith(".jpg") and file.startswith("IMG_"):
            full_path = os.path.join(args.directory, file)

            parsed = parse_filename(file)
            if parsed:
                if args.sort_by == "sequence":
                    sort_key = parsed["sequence"]
                else:  # sort by timestamp
                    sort_key = parsed["timestamp"]
                jpg_files.append((sort_key, full_path, file))

    if not jpg_files:
        print(f"No matching image files found in '{args.directory}'")
        return 1

    # Sort by the chosen method
    jpg_files.sort(key=lambda x: x[0])

    # Write output file
    with open(args.output, "w") as f:
        for sort_key, full_path, filename in jpg_files:
            # Convert path to use /input/ prefix as shown in your example
            output_path = f"/input/{filename}"
            f.write(f"file {output_path}\n")

    sort_method = "sequence number" if args.sort_by == "sequence" else "timestamp"
    print(
        f"Generated {args.output} with {len(jpg_files)} files sorted by {sort_method}"
    )
    print(f"Files sorted from {jpg_files[0][2]} to {jpg_files[-1][2]}")


if __name__ == "__main__":
    main()
