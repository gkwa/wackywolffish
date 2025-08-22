import argparse
import json
import pathlib
import datetime


def parse_iso_datetime(datetime_str):
    """Parse ISO format datetime string to datetime object."""
    return datetime.datetime.fromisoformat(datetime_str)


def calculate_duration_seconds(start_time, end_time):
    """Calculate duration in seconds between two datetime strings."""
    start_dt = parse_iso_datetime(start_time)
    end_dt = parse_iso_datetime(end_time)
    duration = end_dt - start_dt
    return int(duration.total_seconds())


def format_duration(duration_seconds):
    """Format duration seconds into human-readable string (e.g., '7h45m')."""
    hours = duration_seconds // 3600
    minutes = (duration_seconds % 3600) // 60
    seconds = duration_seconds % 60
    
    if hours > 0 and minutes > 0:
        return f"{hours}h{minutes}m"
    elif hours > 0:
        return f"{hours}h"
    elif minutes > 0:
        return f"{minutes}m"
    else:
        return f"{seconds}s"


def update_manifest_durations(manifest_path):
    """Update duration fields in manifest JSON file."""
    manifest_file = pathlib.Path(manifest_path)
    
    if not manifest_file.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    # Read the manifest
    with open(manifest_file, 'r') as f:
        manifest = json.load(f)
    
    # Update each video entry
    updated_count = 0
    for video in manifest.get('videos', []):
        if 'start_time' in video and 'end_time' in video:
            # Calculate duration in seconds
            duration_seconds = calculate_duration_seconds(
                video['start_time'], 
                video['end_time']
            )
            
            # Format human-readable duration
            duration_formatted = format_duration(duration_seconds)
            
            # Update the video entry
            video['duration_seconds'] = duration_seconds
            video['duration'] = duration_formatted
            updated_count += 1
            
            print(f"Updated {video.get('filename', 'unknown')}: {duration_formatted} ({duration_seconds}s)")
    
    # Write back to file
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nUpdated {updated_count} video entries in {manifest_path}")
    return updated_count


def main():
    parser = argparse.ArgumentParser(
        description="Auto-populate duration fields in sourdough starter manifest"
    )
    parser.add_argument(
        'manifest_path',
        nargs='?',
        default='sourdough-starter-manifest.json',
        help='Path to the manifest JSON file (default: sourdough-starter-manifest.json)'
    )
    
    args = parser.parse_args()
    
    try:
        update_manifest_durations(args.manifest_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
