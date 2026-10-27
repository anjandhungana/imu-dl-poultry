from dataclasses import dataclass


IMU_COLUMNS = (
    "device_id",
    "t_unix",
    "ax",
    "ay",
    "az",
    "gx",
    "gy",
    "gz",
    "bat_v",
)


@dataclass(frozen=True)
class AppConfig:
    serial_baud: int = 115_200
    preview_interval_ms: int = 30
    video_fps: float = 30.0
    video_codec: str = "mp4v"
    default_camera_index: int = 0
    camera_width: int = 1920
    camera_height: int = 1080
    camera_fps: float = 30.0
