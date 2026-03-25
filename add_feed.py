"""Append a new feed entry to the sourdough starter manifest."""
# /// script
# requires-python = ">=3.12"
# dependencies = ["dateparser>=1.2"]
# ///

import argparse
import dateparser
import datetime
import json
import pathlib
import sys

DEFAULT_RECIPE = "arachnophobia"


def parse_time(value: str) -> datetime.time:
    for fmt in ("%I:%M%p", "%I:%M %p", "%H:%M:%S", "%H:%M"):
        try:
            return datetime.datetime.strptime(value.strip().upper(), fmt).time()
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"Cannot parse time {value!r}. Use formats like '9:32pm' or '21:32'."
    )


def parse_date(value: str) -> datetime.date:
    result = dateparser.parse(value, settings={"RETURN_AS_TIMEZONE_AWARE": False})
    if result is not None:
        return result.date()
    raise argparse.ArgumentTypeError(
        f"Cannot parse date {value!r}."
    )


def build_entry(args: argparse.Namespace) -> dict:
    feed_dt = datetime.datetime.combine(args.date, args.time)
    return {
        "active_end_time": args.active_end_time,
        "active_time": args.active_time,
        "feed_time": feed_dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "incomplete_record": args.incomplete_record,
        "note": args.note,
        "notes": args.notes,
        "peak_time": args.peak_time,
        "ratio": args.ratio,
        "recipe": args.recipe,
        "starter_grams": args.starter_grams,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append a feed entry to the sourdough manifest."
    )
    parser.add_argument("time", type=parse_time, help="Feed time, e.g. '9:32pm' or '21:32'")
    parser.add_argument(
        "--date",
        type=parse_date,
        default=datetime.date.today(),
        help="Feed date (default: today). Format: YYYY-MM-DD",
    )
    parser.add_argument("--recipe", default=DEFAULT_RECIPE, help=f"Recipe name (default: {DEFAULT_RECIPE})")
    parser.add_argument("--peak-time", default="", dest="peak_time", help="Peak time ISO string (default: empty)")
    parser.add_argument("--active-time", default="", dest="active_time", help="Active time (default: empty)")
    parser.add_argument("--active-end-time", default="", dest="active_end_time", help="Active end time (default: empty)")
    parser.add_argument("--ratio", default="", help="Feeding ratio, e.g. '1:3.25:3.25'")
    parser.add_argument("--starter-grams", default="", dest="starter_grams", help="Starter weight in grams")
    parser.add_argument("--note", default="", help="Single note (default: empty)")
    parser.add_argument("--notes", default="", help="Notes (default: empty)")
    parser.add_argument("--incomplete-record", default="", dest="incomplete_record", help="Incomplete record flag (default: empty)")
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        required=True,
        help="Absolute path to manifest JSON file",
    )
    args = parser.parse_args()

    manifest_path: pathlib.Path = args.manifest
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(manifest_path.read_text())
    entry = build_entry(args)
    data["videos"].append(entry)
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
