#!/usr/bin/env python3
import argparse
import sys
import re
import pathlib
import contextlib
import select
import typing

# Constants
SCRIPT_EXECUTABLE_MODE = 0o755
DEFAULT_SCRIPT_NAME = "run_ffmpeg.sh"

# Exit codes
EXIT_SUCCESS = 0
EXIT_NO_FILES = 1
EXIT_INTERRUPTED = 2

# Type aliases
ParsedFile = typing.Dict[str, typing.Union[str, int, typing.Tuple[str, str, str]]]
MediaFile = typing.Tuple[typing.Union[int, typing.Tuple[str, str, str]], str, str, str]
ParserFunction = typing.Callable[[str], typing.Optional[ParsedFile]]


def parse_filename_aatp(filepath: str) -> typing.Optional[ParsedFile]:
    """
    Parse filename like IMG_20250728_115906_AATP1401.jpg
    Returns dict with date, time, and sequence number (AATP prefix removed)
    """
    filename = pathlib.Path(filepath).name
    # Match pattern: IMG_YYYYMMDD_HHMMSS_AATPNNNN.jpg and extract just the number part
    match = re.match(r"IMG_(\d{8})_(\d{6})_AATP(\d+)\.jpg$", filename)
    if match:
        date_str, time_str, sequence_str = match.groups()
        return {
            "date": date_str,
            "time": time_str,
            "sequence": int(sequence_str),
            "timestamp": (date_str, time_str, sequence_str),
            "filepath": filepath,
            "parser_type": "aatp",
        }
    return None


def parse_filename_simple(filepath: str) -> typing.Optional[ParsedFile]:
    """
    Parse filename like IMG_20250908_150139.jpg
    Returns dict with date, time, and synthetic sequence number based on time
    """
    filename = pathlib.Path(filepath).name
    # Match pattern: IMG_YYYYMMDD_HHMMSS.jpg
    match = re.match(r"IMG_(\d{8})_(\d{6})\.jpg$", filename)
    if match:
        date_str, time_str = match.groups()
        # Create synthetic sequence from time for sorting
        sequence = int(time_str)
        return {
            "date": date_str,
            "time": time_str,
            "sequence": sequence,
            "timestamp": (date_str, time_str, "000"),
            "filepath": filepath,
            "parser_type": "simple",
        }
    return None


def get_parser_functions(
    pattern_types: typing.Optional[typing.List[str]] = None,
) -> typing.List[ParserFunction]:
    """Return list of parser functions based on pattern types"""
    all_parsers = {
        "aatp": parse_filename_aatp,
        "simple": parse_filename_simple,
    }

    if pattern_types is None:
        return list(all_parsers.values())

    return [all_parsers[ptype] for ptype in pattern_types if ptype in all_parsers]


def needs_quotes(path: str) -> bool:
    """Check if path needs quotes (has spaces or special characters)"""
    # Don't quote command substitutions
    if path.startswith("$(") and path.endswith(")"):
        return False
    # Check for spaces, special shell characters, etc.
    special_chars = r'[ \t\n\r\f\v$`"\'\\;|&<>(){}*?[\]~#!]'
    return bool(re.search(special_chars, path))


def format_path(path: typing.Union[str, pathlib.Path]) -> str:
    """Format path with quotes only if needed"""
    if needs_quotes(str(path)):
        return f"'{path}'"
    return str(path)


def get_sort_key(
    parsed: ParsedFile, sort_by: str
) -> typing.Union[int, typing.Tuple[str, str, str]]:
    """Get the appropriate sort key based on sort method"""
    if sort_by == "sequence":
        sequence = parsed["sequence"]
        assert isinstance(sequence, int)
        return sequence
    timestamp = parsed["timestamp"]
    assert isinstance(timestamp, tuple)
    return timestamp


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Generate ffmpeg bash script from sorted image files"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input file containing image paths (default: read from stdin)",
    )
    parser.add_argument(
        "--script-output",
        default=DEFAULT_SCRIPT_NAME,
        help=f"Output bash script filename, use '-' for stdout (default: {DEFAULT_SCRIPT_NAME})",
    )
    parser.add_argument(
        "-s",
        "--sort-by",
        choices=["timestamp", "sequence"],
        default="sequence",
        help="Sort by sequence (AATP number) or timestamp (date/time) (default: sequence)",
    )
    parser.add_argument(
        "-p",
        "--patterns",
        nargs="*",
        choices=["aatp", "simple"],
        help="Filename patterns to try: 'aatp' for IMG_DATE_TIME_AATPNNNN.jpg, 'simple' for IMG_DATE_TIME.jpg (default: all patterns)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Don't print summary information",
    )
    return parser.parse_args()


def try_parse_with_functions(
    filepath: str, parser_functions: typing.List[ParserFunction]
) -> typing.Optional[ParsedFile]:
    """Try parsing filepath with multiple parser functions, return first successful match"""
    for parser_func in parser_functions:
        result = parser_func(filepath)
        if result:
            return result
    return None


def check_stdin_available() -> bool:
    """Check if stdin has data available without blocking"""
    if sys.stdin.isatty():
        return False

    # Use select to check if data is available
    try:
        ready, _, _ = select.select([sys.stdin], [], [], 0)
        return bool(ready)
    except (OSError, ValueError):
        # select might not work on all platforms/situations
        return True  # Assume data is available


def read_and_parse_files(
    input_source: typing.TextIO,
    sort_by: str,
    parser_functions: typing.List[ParserFunction],
    is_stdin: bool = False,
    quiet: bool = False,
) -> typing.Tuple[typing.List[MediaFile], typing.Set[str]]:
    """Read files from input source and parse them into sorted list using provided parser functions"""
    media_files: typing.List[MediaFile] = []
    mount_paths: typing.Set[str] = set()

    # Show helpful message if waiting for stdin
    if is_stdin and not check_stdin_available() and not quiet:
        print("Waiting for input on stdin (Ctrl+C to cancel)...", file=sys.stderr)

    try:
        for line in input_source:
            filepath = line.strip()
            if not filepath:
                continue

            parsed = try_parse_with_functions(filepath, parser_functions)
            if parsed:
                sort_key = get_sort_key(parsed, sort_by)
                path = pathlib.Path(str(parsed["filepath"]))
                parser_type = parsed["parser_type"]
                assert isinstance(parser_type, str)
                media_files.append(
                    (sort_key, str(parsed["filepath"]), path.name, parser_type)
                )
                mount_paths.add(str(path.parent))
    except KeyboardInterrupt:
        if not quiet:
            if is_stdin:
                print("\nInterrupted while reading from stdin", file=sys.stderr)
            else:
                print("\nOperation interrupted", file=sys.stderr)
        raise

    media_files.sort(key=lambda x: x[0])
    return media_files, mount_paths


def create_manifest_content(media_files: typing.List[MediaFile]) -> typing.List[str]:
    """Create the manifest file content"""
    manifest_content: typing.List[str] = []
    for sort_key, full_path, filename, parser_type in media_files:
        docker_path = f"/input/{filename}"
        manifest_content.append(f"file {format_path(docker_path)}\n")
    return manifest_content


def write_manifest_section(
    f: typing.TextIO, manifest_content: typing.List[str]
) -> None:
    """Write the manifest file creation section"""
    f.write("# Create manifest file\n")
    f.write("cat > ffmpeg_list.txt << 'EOF'\n")
    for line in manifest_content:
        f.write(line)
    f.write("EOF\n\n")


def write_docker_command(f: typing.TextIO, mount_paths: typing.Set[str]) -> None:
    """Write the docker command section"""
    # Build mount volume arguments
    mount_args = []
    for mount_path in sorted(mount_paths):
        mount_args.append(f"-v {format_path(mount_path)}:/input")

    mount_volumes = " \\\n".join(mount_args)

    docker_command = f"""# Run ffmpeg in docker
docker run --rm --name wackywolffish \\
-v {format_path("$(pwd)")}:/workspace \\
{mount_volumes} \\
jrottenberg/ffmpeg:latest \\
-y \\
-f concat \\
-safe 0 \\
-i /workspace/ffmpeg_list.txt \\
-r 15 \\
-vf scale=1280:720 \\
-c:v libx264 \\
-preset fast \\
-crf 28 \\
-pix_fmt yuv420p \\
/workspace/timelapse.mp4
"""

    f.write(docker_command)


def get_output_context(output_file: str) -> typing.ContextManager[typing.TextIO]:
    """Get output context manager for file or stdout"""
    if output_file == "-":
        return contextlib.nullcontext(sys.stdout)
    return open(output_file, "w")


def generate_script(
    output_file: str, media_files: typing.List[MediaFile], mount_paths: typing.Set[str]
) -> None:
    """Generate the complete bash script"""
    manifest_content = create_manifest_content(media_files)

    with get_output_context(output_file) as f:
        f.write("#!/bin/bash\n")
        f.write("# Generated ffmpeg script\n\n")

        write_manifest_section(f, manifest_content)
        write_docker_command(f, mount_paths)

    # Make the script executable only if it's a file (not stdout)
    if output_file != "-":
        pathlib.Path(output_file).chmod(SCRIPT_EXECUTABLE_MODE)


def print_summary(
    output_file: str,
    media_files: typing.List[MediaFile],
    sort_by: str,
    used_patterns: typing.List[str],
) -> None:
    """Print summary information to stderr"""
    sort_method = "sequence number" if sort_by == "sequence" else "timestamp"
    pattern_summary = ", ".join(used_patterns) if used_patterns else "all"

    output_desc = "stdout" if output_file == "-" else output_file
    print(
        f"Generated script to {output_desc} with {len(media_files)} files sorted by {sort_method}",
        file=sys.stderr,
    )
    print(f"Used patterns: {pattern_summary}", file=sys.stderr)
    if media_files:
        print(
            f"Files sorted from {media_files[0][2]} to {media_files[-1][2]}",
            file=sys.stderr,
        )


def get_used_patterns(media_files: typing.List[MediaFile]) -> typing.List[str]:
    """Extract unique parser types used from media files"""
    return list(set(item[3] for item in media_files))


def get_input_source(
    input_file: typing.Optional[str],
) -> typing.ContextManager[typing.TextIO]:
    """Get input source context manager for file or stdin"""
    if input_file:
        return open(input_file, "r")
    return contextlib.nullcontext(sys.stdin)


def load_media_files(
    args: argparse.Namespace,
) -> typing.Tuple[typing.List[MediaFile], typing.Set[str]]:
    """Load and parse media files from input source"""
    parser_functions = get_parser_functions(args.patterns)

    with get_input_source(args.input_file) as input_source:
        is_stdin = args.input_file is None
        return read_and_parse_files(
            input_source, args.sort_by, parser_functions, is_stdin, args.quiet
        )


def handle_error(
    e: typing.Union[KeyboardInterrupt, IOError], args: argparse.Namespace
) -> int:
    """Handle different types of errors and return appropriate exit code"""
    if isinstance(e, KeyboardInterrupt):
        return EXIT_INTERRUPTED
    elif isinstance(e, IOError):
        if not args.quiet:
            print(f"Error opening input file '{args.input_file}': {e}", file=sys.stderr)
        return EXIT_NO_FILES
    else:
        raise e


def process_files(args: argparse.Namespace) -> int:
    """Process files and generate script, handling all errors"""
    try:
        media_files, mount_paths = load_media_files(args)
    except (KeyboardInterrupt, IOError) as e:
        return handle_error(e, args)

    if not media_files:
        if not args.quiet:
            print("No matching image files found in input", file=sys.stderr)
        return EXIT_NO_FILES

    try:
        generate_script(args.script_output, media_files, mount_paths)

        if not args.quiet:
            used_patterns = get_used_patterns(media_files)
            print_summary(args.script_output, media_files, args.sort_by, used_patterns)

    except KeyboardInterrupt:
        if not args.quiet:
            print("\nOperation interrupted during script generation", file=sys.stderr)
        return EXIT_INTERRUPTED

    return EXIT_SUCCESS


def main() -> int:
    """Main entry point"""
    args = parse_arguments()
    return process_files(args)


if __name__ == "__main__":
    sys.exit(main())
