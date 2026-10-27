from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote


def format_elapsed(seconds: float) -> str:
    total_microseconds = max(0, round(seconds * 1_000_000))
    hours, remainder = divmod(total_microseconds, 3_600_000_000)
    minutes, remainder = divmod(remainder, 60_000_000)
    secs, microseconds = divmod(remainder, 1_000_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{microseconds:06d}"


def media_url(base_url: str, relative_path: Path) -> str:
    path = quote(relative_path.as_posix(), safe="/")
    return f"{base_url.rstrip('/')}/{path}"


def prepare_browser_video(source: Path, destination: Path) -> None:
    if destination.is_file() and destination.stat().st_mtime >= source.stat().st_mtime:
        return
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to create browser-compatible H.264 video")

    command = [
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination),
    ]
    subprocess.run(command, check=True)


def prepare_session(
    session_dir: Path,
    project_root: Path,
    processed_root: Path,
    base_url: str,
) -> dict | None:
    source_csv = session_dir / "imu.csv"
    video = session_dir / "video.mp4"
    if not source_csv.is_file() or not video.is_file():
        print(f"Skipping incomplete session: {session_dir.name}")
        return None

    destination_dir = processed_root / session_dir.name
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination_csv = destination_dir / "imu.csv"
    destination_video = destination_dir / "video.mp4"
    prepare_browser_video(video, destination_video)

    with source_csv.open(newline="", encoding="utf-8") as source, destination_csv.open(
        "w", newline="", encoding="utf-8"
    ) as destination:
        reader = csv.DictReader(source)
        required = {"elapsed_time_s", "ax", "ay", "az", "gx", "gy", "gz", "bat_v"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{source_csv} is missing columns: {sorted(missing)}")

        columns = ["time", "ax", "ay", "az", "gx", "gy", "gz", "bat_v"]
        rows = list(reader)
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()

        # Label Studio anchors synchronized time series at their first timestamp.
        # A zero-time placeholder preserves any real delay before IMU data begins.
        if rows and float(rows[0]["elapsed_time_s"]) > 0.001:
            first = rows[0]
            writer.writerow(
                {
                    "time": format_elapsed(0.0),
                    "ax": first["ax"],
                    "ay": first["ay"],
                    "az": first["az"],
                    "gx": first["gx"],
                    "gy": first["gy"],
                    "gz": first["gz"],
                    "bat_v": first["bat_v"],
                }
            )

        for row in rows:
            writer.writerow(
                {
                    "time": format_elapsed(float(row["elapsed_time_s"])),
                    "ax": row["ax"],
                    "ay": row["ay"],
                    "az": row["az"],
                    "gx": row["gx"],
                    "gy": row["gy"],
                    "gz": row["gz"],
                    "bat_v": row["bat_v"],
                }
            )

    return {
        "data": {
            "session": session_dir.name,
            "video": media_url(base_url, destination_video.relative_to(project_root)),
            "imu": media_url(base_url, source_csv.relative_to(project_root)),
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare recorder sessions for Label Studio")
    parser.add_argument(
        "--recordings",
        type=Path,
        default=None,
        help="Recorder sessions directory (defaults to <project>/recordings)",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8765",
        help="URL of the local media server",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    recordings = (args.recordings or project_root / "recordings").resolve()
    processed_root = project_root / "label_studio" / "processed"
    processed_root.mkdir(parents=True, exist_ok=True)

    tasks = []
    for session_dir in sorted(recordings.glob("session_*")):
        if session_dir.is_dir():
            task = prepare_session(
                session_dir, project_root, processed_root, args.base_url
            )
            if task:
                tasks.append(task)

    output = project_root / "label_studio" / "tasks.json"
    output.write_text(json.dumps(tasks, indent=2), encoding="utf-8")
    print(f"Prepared {len(tasks)} task(s): {output}")


if __name__ == "__main__":
    main()
