import argparse
import json
import pathlib
import sys


def load_manifest(manifest_path: pathlib.Path) -> dict:
    """Load the sourdough starter manifest JSON file."""
    if not manifest_path.exists():
        print(f"Error: Manifest file {manifest_path} does not exist")
        sys.exit(1)
    
    with open(manifest_path, 'r') as f:
        return json.load(f)


def save_manifest(manifest_path: pathlib.Path, data: dict) -> None:
    """Save the manifest JSON file with proper formatting and sorted keys."""
    with open(manifest_path, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)


def get_mp4_files(directory: pathlib.Path) -> set:
    """Get all MP4 files in the directory."""
    return {f.name for f in directory.glob("*.mp4")}


def add_missing_timestamps(video_record: dict) -> bool:
    """Add missing timestamp keys to a video record. Returns True if modified."""
    required_keys = ["active_start_time", "active_end_time"]
    modified = False
    
    for key in required_keys:
        if key not in video_record:
            video_record[key] = ""
            modified = True
    
    return modified


def report_missing_files(manifest_data: dict, existing_files: set) -> None:
    """Report missing MP4 files."""
    manifest_files = set()
    missing_from_disk = []
    
    for video in manifest_data.get("videos", []):
        if "filename" in video:
            filename = video["filename"]
            manifest_files.add(filename)
            if filename not in existing_files:
                missing_from_disk.append(filename)
    
    missing_from_manifest = existing_files - manifest_files
    
    if missing_from_disk:
        print("MP4 files in manifest but missing from disk:")
        for filename in sorted(missing_from_disk):
            print(f"  {filename}")
    
    if missing_from_manifest:
        print("MP4 files on disk but missing from manifest:")
        for filename in sorted(missing_from_manifest):
            print(f"  {filename}")


def report_incomplete_records(manifest_data: dict) -> None:
    """Report records marked as incomplete."""
    incomplete_records = []
    
    for video in manifest_data.get("videos", []):
        if video.get("incomplete_record", False):
            sequence = video.get("sequence", "unknown")
            filename = video.get("filename", "no filename")
            incomplete_records.append((sequence, filename))
    
    if incomplete_records:
        print("Incomplete records:")
        for sequence, filename in sorted(incomplete_records):
            print(f"  Sequence {sequence}: {filename}")


def main():
    parser = argparse.ArgumentParser(description="Fix sourdough starter manifest timestamps and report missing files")
    parser.add_argument("--manifest", default="sourdough-starter-manifest.json", 
                       help="Path to manifest file (default: sourdough-starter-manifest.json)")
    parser.add_argument("--directory", default=".", 
                       help="Directory to scan for MP4 files (default: current directory)")
    
    args = parser.parse_args()
    
    manifest_path = pathlib.Path(args.manifest)
    directory = pathlib.Path(args.directory)
    
    if not directory.exists():
        print(f"Error: Directory {directory} does not exist")
        sys.exit(1)
    
    manifest_data = load_manifest(manifest_path)
    existing_files = get_mp4_files(directory)
    
    # Add missing timestamp keys
    modified = False
    for video in manifest_data.get("videos", []):
        if add_missing_timestamps(video):
            modified = True
    
    # Always save manifest to ensure sorted keys
    save_manifest(manifest_path, manifest_data)
    if modified:
        print("Updated manifest with missing timestamp keys")
    
    # Report missing files
    report_missing_files(manifest_data, existing_files)
    
    # Report incomplete records
    report_incomplete_records(manifest_data)


if __name__ == "__main__":
    main()
