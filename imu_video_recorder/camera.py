from __future__ import annotations

import cv2
import numpy as np


class CameraError(RuntimeError):
    pass


class Camera:
    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self.index: int | None = None

    @property
    def is_open(self) -> bool:
        return self._capture is not None and self._capture.isOpened()

    @property
    def frame_size(self) -> tuple[int, int]:
        if not self.is_open:
            raise CameraError("Camera is not open")
        assert self._capture is not None
        width = int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return width, height

    @property
    def measured_fps(self) -> float:
        if not self.is_open:
            return 0.0
        assert self._capture is not None
        return float(self._capture.get(cv2.CAP_PROP_FPS) or 0.0)

    def open(
        self, index: int, width: int = 1920, height: int = 1080, fps: float = 30.0
    ) -> None:
        self.close()
        capture = cv2.VideoCapture(index)
        if not capture.isOpened():
            capture.release()
            raise CameraError(f"Could not open camera {index}")

        # MJPG commonly allows USB webcams to expose their full-resolution 16:9 mode.
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        capture.set(cv2.CAP_PROP_FPS, fps)
        self._capture = capture
        self.index = index

    def read(self) -> np.ndarray | None:
        if not self.is_open:
            return None
        assert self._capture is not None
        ok, frame = self._capture.read()
        return frame if ok else None

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = None
        self.index = None
