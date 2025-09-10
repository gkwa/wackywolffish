#!/usr/bin/env python3

import argparse
import json
import yaml
from typing import Dict, List, Any
from collections import defaultdict
from rich.console import Console
from rich.table import Table


def parse_duration_seconds(seconds: int) -> str:
    """Convert seconds to human-friendly duration format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    remaining_seconds = seconds % 60

    if hours > 0:
        if minutes > 0:
            return f"{hours}h{minutes}m"
        return f"{hours}h"
    elif minutes > 0:
        if remaining_seconds > 30:  # Round up if more than 30 seconds
            return f"{minutes + 1}m" if minutes < 59 else f"{hours + 1}h"
        return f"{minutes}m"
    else:
        return f"{remaining_seconds}s"


def load_data(file_path: str) -> Dict[str, Any]:
    """Load data from JSON or YAML file"""
    with open(file_path, "r") as f:
        if file_path.lower().endswith(".json"):
            return json.load(f)
        elif file_path.lower().endswith((".yml", ".yaml")):
            return yaml.safe_load(f)
        else:
            # Try to detect format by content
            content = f.read()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    return yaml.safe_load(content)
                except yaml.YAMLError:
                    raise ValueError(
                        "File format not recognized. Please use .json or .yaml/.yml extension"
                    )


def group_by_ratio(videos: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group videos by ratio"""
    grouped = defaultdict(list)

    for video in videos:
        ratio = video.get("ratio", "unknown")
        grouped[ratio].append(video)

    return dict(grouped)


def calculate_duration_differences(
    grouped_data: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    """Calculate duration statistics for each ratio group"""
    results = {}

    for ratio, videos in grouped_data.items():
        if not videos:
            continue

        durations = [v["duration_seconds"] for v in videos if "duration_seconds" in v]
        if not durations:
            continue

        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        results[ratio] = {
            "count": len(videos),
            "avg_duration_seconds": avg_duration,
            "min_duration_seconds": min_duration,
            "max_duration_seconds": max_duration,
            "avg_duration_human": parse_duration_seconds(int(avg_duration)),
            "min_duration_human": parse_duration_seconds(min_duration),
            "max_duration_human": parse_duration_seconds(max_duration),
            "videos": videos,
        }

    return results


def display_results(results: Dict[str, Dict[str, Any]], console: Console):
    """Display results using Rich table"""
    table = Table(title="Sourdough Starter Peak Times by Ratio")

    table.add_column("Ratio", style="cyan", no_wrap=True)
    table.add_column("Count", justify="center", style="magenta")
    table.add_column("Avg Peak Time", justify="center", style="green")
    table.add_column("Min Peak Time", justify="center", style="blue")
    table.add_column("Max Peak Time", justify="center", style="red")
    table.add_column("Range", justify="center", style="yellow")

    # Sort by ratio for consistent display
    sorted_results = sorted(
        results.items(), key=lambda x: x[0] if x[0] != "unknown" else "zzz"
    )

    for ratio, data in sorted_results:
        range_diff = data["max_duration_seconds"] - data["min_duration_seconds"]
        range_human = (
            parse_duration_seconds(int(range_diff)) if range_diff > 0 else "0m"
        )

        table.add_row(
            ratio,
            str(data["count"]),
            data["avg_duration_human"],
            data["min_duration_human"],
            data["max_duration_human"],
            range_human,
        )

    console.print(table)


def display_detailed_results(results: Dict[str, Dict[str, Any]], console: Console):
    """Display detailed results for each ratio"""
    for ratio, data in sorted(results.items()):
        console.print(f"\n[bold cyan]Ratio {ratio}:[/bold cyan]")

        detail_table = Table(show_header=True, header_style="bold magenta")
        detail_table.add_column("Sequence", style="dim")
        detail_table.add_column("Start Time", style="blue")
        detail_table.add_column("Peak Time", style="green")
        detail_table.add_column("Duration", style="yellow")
        detail_table.add_column("Notes", style="dim")

        for video in data["videos"]:
            notes = (
                video.get("notes", "")[:50] + "..."
                if len(video.get("notes", "")) > 50
                else video.get("notes", "")
            )

            detail_table.add_row(
                str(video.get("sequence", "N/A")),
                video.get("start_time", "N/A"),
                video.get("end_time", "N/A"),
                parse_duration_seconds(video.get("duration_seconds", 0)),
                notes,
            )

        console.print(detail_table)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze sourdough starter time-lapse data"
    )
    parser.add_argument("file_path", help="Path to JSON or YAML manifest file")
    parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        help="Show detailed results for each ratio",
    )
    parser.add_argument(
        "--sort-by",
        choices=["ratio", "duration", "count"],
        default="ratio",
        help="Sort results by specified field",
    )

    args = parser.parse_args()

    console = Console()

    try:
        # Load data
        data = load_data(args.file_path)
        videos = data.get("videos", [])

        if not videos:
            console.print("[red]No videos found in the manifest file[/red]")
            return

        # Group by ratio and calculate statistics
        grouped_data = group_by_ratio(videos)
        results = calculate_duration_differences(grouped_data)

        if not results:
            console.print("[red]No valid duration data found[/red]")
            return

        # Display results
        console.print(
            f"[bold]Analyzing {len(videos)} video records from {args.file_path}[/bold]\n"
        )
        display_results(results, console)

        if args.detailed:
            display_detailed_results(results, console)

    except FileNotFoundError:
        console.print(f"[red]Error: File '{args.file_path}' not found[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")


if __name__ == "__main__":
    main()
