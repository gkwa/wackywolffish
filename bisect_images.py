#!/usr/bin/env python3

import sys
import pathlib
import re
import subprocess
import typing
import dataclasses


@dataclasses.dataclass
class ImageInfo:
    path: pathlib.Path
    timestamp: str
    atp_number: int


@dataclasses.dataclass
class BisectState:
    left: int
    right: int
    current_index: int


def parse_image_filename(path: pathlib.Path) -> typing.Optional[ImageInfo]:
    """Parse image filename to extract timestamp and ATP number."""
    # Pattern: IMG_YYYYMMDD_HHMMSS_AATPNNNN.jpg
    pattern = r"IMG_(\d{8}_\d{6})_AATP(\d{4})\."
    match = re.search(pattern, path.name)

    if match:
        timestamp = match.group(1)
        atp_number = int(match.group(2))
        return ImageInfo(path=path, timestamp=timestamp, atp_number=atp_number)

    return None


def sort_images(image_paths: typing.List[pathlib.Path]) -> typing.List[ImageInfo]:
    """Sort images by timestamp, then by ATP number."""
    image_infos = []

    for path in image_paths:
        info = parse_image_filename(path)
        if info:
            image_infos.append(info)

    # Sort by timestamp first, then by ATP number
    image_infos.sort(key=lambda x: (x.timestamp, x.atp_number))

    return image_infos


def open_image(image_path: pathlib.Path):
    """Open image using the system's default image viewer."""
    try:
        subprocess.run(["open", str(image_path)], check=True)
    except subprocess.CalledProcessError:
        print(f"Error: Could not open {image_path}", file=sys.stderr)
    except FileNotFoundError:
        print("Error: 'open' command not found. Are you on macOS?", file=sys.stderr)


def main():
    # Read paths from stdin
    image_paths = []
    for line in sys.stdin:
        path = pathlib.Path(line.strip())
        if path.exists() and path.is_file():
            image_paths.append(path)

    if not image_paths:
        print("No valid image paths provided", file=sys.stderr)
        sys.exit(1)

    # Sort images
    sorted_images = sort_images(image_paths)

    if not sorted_images:
        print("No images with valid ATP format found", file=sys.stderr)
        sys.exit(1)

    # Binary search state and history
    left = 0
    right = len(sorted_images) - 1
    current_index = (left + right) // 2

    # History stack to track states for redo functionality
    history = []

    print(f"Loaded {len(sorted_images)} images")
    print(
        "Commands: n=bisect right (later), p=bisect left (earlier), r [count]=redo last move(s), q=quit"
    )
    print(f"Range: [{left}, {right}], Current: {current_index}")

    # Open middle image and output its path
    open_image(sorted_images[current_index].path)
    print(
        f"[{current_index + 1}/{len(sorted_images)}] {sorted_images[current_index].path}"
    )

    # Reopen stdin to read from terminal
    sys.stdin = open("/dev/tty", "r")

    while True:
        try:
            command = input().strip().lower()

            if command == "q":
                break
            elif command == "n":  # bisect right (go to later images)
                if left < right:
                    # Save current state to history
                    history.append(BisectState(left, right, current_index))

                    left = current_index + 1
                    current_index = (left + right) // 2
                    open_image(sorted_images[current_index].path)
                    print(f"Range: [{left}, {right}], Current: {current_index}")
                    print(
                        f"[{current_index + 1}/{len(sorted_images)}] {sorted_images[current_index].path}"
                    )
                else:
                    print("Cannot bisect further", file=sys.stderr)
            elif command == "p":  # bisect left (go to earlier images)
                if left < right:
                    # Save current state to history
                    history.append(BisectState(left, right, current_index))

                    right = current_index - 1
                    current_index = (left + right) // 2
                    open_image(sorted_images[current_index].path)
                    print(f"Range: [{left}, {right}], Current: {current_index}")
                    print(
                        f"[{current_index + 1}/{len(sorted_images)}] {sorted_images[current_index].path}"
                    )
                else:
                    print("Cannot bisect further", file=sys.stderr)
            elif command.startswith("r"):  # redo functionality
                parts = command.split()
                redo_count = 1  # default to redoing 1 move

                if len(parts) > 1:
                    try:
                        redo_count = int(parts[1])
                    except ValueError:
                        print(
                            "Invalid redo count. Use 'r' or 'r <number>'",
                            file=sys.stderr,
                        )
                        continue

                if redo_count <= 0:
                    print("Redo count must be positive", file=sys.stderr)
                    continue

                if redo_count > len(history):
                    print(
                        f"Cannot redo {redo_count} moves, only {len(history)} moves in history",
                        file=sys.stderr,
                    )
                    continue

                # Pop the specified number of states from history
                for _ in range(redo_count):
                    if history:
                        state = history.pop()
                        left = state.left
                        right = state.right
                        current_index = state.current_index

                open_image(sorted_images[current_index].path)
                print(f"Redid {redo_count} move(s)")
                print(f"Range: [{left}, {right}], Current: {current_index}")
                print(
                    f"[{current_index + 1}/{len(sorted_images)}] {sorted_images[current_index].path}"
                )
            else:
                print(
                    "Unknown command. Use n=bisect right (later), p=bisect left (earlier), r [count]=redo last move(s), q=quit",
                    file=sys.stderr,
                )

        except EOFError:
            break
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
