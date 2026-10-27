from __future__ import annotations

from dataclasses import dataclass
from queue import Empty, Queue
from threading import Event, Thread
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # The GUI explains how to install the missing dependency.
    serial = None
    list_ports = None


class SerialReaderError(RuntimeError):
    pass


@dataclass(frozen=True)
class SerialLine:
    received_ns: int
    text: str


def available_ports() -> list[str]:
    if list_ports is None:
        return []
    return [port.device for port in list_ports.comports()]


class SerialReader:
    def __init__(self, baud: int) -> None:
        self.baud = baud
        self.lines: Queue[SerialLine] = Queue()
        self._serial = None
        self._stop = Event()
        self._thread: Thread | None = None
        self.last_error: str | None = None

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    @property
    def port(self) -> str | None:
        return self._serial.port if self.is_connected else None

    def connect(self, port: str) -> None:
        if serial is None:
            raise SerialReaderError("pyserial is missing. Run: pip install -r requirements.txt")
        self.disconnect()
        try:
            self._serial = serial.Serial(port, self.baud, timeout=0.1)
        except Exception as exc:
            self._serial = None
            raise SerialReaderError(f"Could not open {port}: {exc}") from exc
        self.last_error = None
        self._stop.clear()
        self._thread = Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def clear_buffer(self) -> None:
        if self.is_connected:
            self._serial.reset_input_buffer()
        while True:
            try:
                self.lines.get_nowait()
            except Empty:
                break

    def disconnect(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self._thread = None
        if self._serial is not None:
            self._serial.close()
        self._serial = None

    def _read_loop(self) -> None:
        while not self._stop.is_set() and self.is_connected:
            try:
                raw = self._serial.readline()
                if raw:
                    text = raw.decode("utf-8", errors="replace").strip()
                    if text:
                        self.lines.put(SerialLine(time.monotonic_ns(), text))
            except Exception as exc:
                self.last_error = str(exc)
                self._stop.set()
