from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
import time

import cv2
import numpy as np

from .config import IMU_COLUMNS
from .serial_reader import SerialLine


class RecorderError(RuntimeError):
    pass


class SessionRecorder:
    def __init__(self) -> None:
        self.session_dir: Path | None = None
        self.start_ns: int | None = None
        self.frame_count = 0
        self.imu_count = 0
        self._video = None
        self._imu_file = None
        self._imu_writer = None
        self._frames_file = None
        self._frames_writer = None
        self._metadata: dict = {}

    @property
    def is_recording(self) -> bool:
        return self.start_ns is not None

    def start(
        self,
        output_root: Path,
        frame_size: tuple[int, int],
        fps: float,
        codec: str,
        camera_index: int,
        serial_port: str,
        serial_baud: int,
    ) -> Path:
        if self.is_recording:
            raise RecorderError("A recording is already active")

        session_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        session_dir = output_root.expanduser().resolve() / session_name
        session_dir.mkdir(parents=True, exist_ok=False)

        fourcc = cv2.VideoWriter_fourcc(*codec)
        video = cv2.VideoWriter(
            str(session_dir / "video.mp4"), fourcc, fps, frame_size
        )
        if not video.isOpened():
            raise RecorderError("Could not create video.mp4")

        self._imu_file = (session_dir / "imu.csv").open("w", newline="", encoding="utf-8")
        self._imu_writer = csv.writer(self._imu_file)
        self._imu_writer.writerow(("elapsed_time_s",) + IMU_COLUMNS)

        self._frames_file = (session_dir / "video_frames.csv").open(
            "w", newline="", encoding="utf-8"
        )
        self._frames_writer = csv.writer(self._frames_file)
        self._frames_writer.writerow(("frame_index", "elapsed_time_s"))

        self.session_dir = session_dir
        self._video = video
        self.frame_count = 0
        self.imu_count = 0
        self.start_ns = time.monotonic_ns()
        self._metadata = {
            "started_at": datetime.now().astimezone().isoformat(),
            "camera_index": camera_index,
            "frame_width": frame_size[0],
            "frame_height": frame_size[1],
            "video_fps": fps,
            "serial_port": serial_port,
            "serial_baud": serial_baud,
            "imu_target_hz": 20,
        }
        return session_dir

    def write_frame(self, frame: np.ndarray, captured_ns: int) -> None:
        if not self.is_recording:
            return
        self._video.write(frame)
        elapsed = (captured_ns - self.start_ns) / 1_000_000_000
        self._frames_writer.writerow((self.frame_count, f"{elapsed:.9f}"))
        self.frame_count += 1

    def write_imu(self, line: SerialLine) -> bool:
        if not self.is_recording or line.received_ns < self.start_ns:
            return False
        if line.text.startswith("#") or line.text.startswith("device_id,"):
            return False
        values = [value.strip() for value in line.text.split(",")]
        if len(values) != len(IMU_COLUMNS):
            return False
        elapsed = (line.received_ns - self.start_ns) / 1_000_000_000
        self._imu_writer.writerow((f"{elapsed:.9f}",) + tuple(values))
        self.imu_count += 1
        return True

    def stop(self) -> Path | None:
        if not self.is_recording:
            return self.session_dir

        stopped_at = datetime.now().astimezone().isoformat()
        duration_s = (time.monotonic_ns() - self.start_ns) / 1_000_000_000
        self._video.release()
        self._imu_file.close()
        self._frames_file.close()
        self._metadata.update(
            {
                "stopped_at": stopped_at,
                "duration_s": duration_s,
                "video_frame_count": self.frame_count,
                "imu_sample_count": self.imu_count,
            }
        )
        with (self.session_dir / "session.json").open("w", encoding="utf-8") as file:
            json.dump(self._metadata, file, indent=2)

        self.start_ns = None
        self._video = None
        self._imu_file = None
        self._imu_writer = None
        self._frames_file = None
        self._frames_writer = None
        return self.session_dir
