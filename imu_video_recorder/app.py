from __future__ import annotations

from pathlib import Path
from queue import Empty
import time
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk

from .camera import Camera, CameraError
from .config import AppConfig
from .recorder import RecorderError, SessionRecorder
from .serial_reader import SerialReader, SerialReaderError, available_ports


class RecorderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._configure_readable_ui()
        self.config = AppConfig()
        self.camera = Camera()
        self.serial = SerialReader(self.config.serial_baud)
        self.recorder = SessionRecorder()
        self.preview_image = None

        root.title("IMU + Video Recorder")
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.port_var = tk.StringVar()
        self.camera_var = tk.IntVar(value=self.config.default_camera_index)
        self.output_var = tk.StringVar(value=str(Path.cwd() / "recordings"))
        self.status_var = tk.StringVar(value="Open the camera and connect the receiver")
        self.count_var = tk.StringVar(value="Frames: 0   IMU samples: 0")

        self._build_ui()
        self.refresh_ports()
        self.root.after(self.config.preview_interval_ms, self._update)

    def _configure_readable_ui(self) -> None:
        """Set comfortable fonts and spacing without relying on OS defaults."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        is_4k = screen_width >= 3000 or screen_height >= 1800
        font_size = 18 if is_4k else 13
        control_padding = (16, 10) if is_4k else (10, 7)
        font_family = "DejaVu Sans"

        for font_name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkMenuFont",
            "TkHeadingFont",
            "TkCaptionFont",
        ):
            try:
                tkfont.nametofont(font_name).configure(
                    family=font_family, size=font_size
                )
            except tk.TclError:
                pass

        ui_font = (font_family, font_size)
        style = ttk.Style(self.root)
        style.configure("TButton", font=ui_font, padding=control_padding)
        style.configure("TLabel", font=ui_font)
        style.configure("TEntry", font=ui_font, padding=8 if is_4k else 5)
        style.configure("TCombobox", font=ui_font, padding=8 if is_4k else 5)
        style.configure("TSpinbox", font=ui_font, padding=8 if is_4k else 5)
        self.root.option_add("*TCombobox*Listbox.font", ui_font)

    def _build_ui(self) -> None:
        controls = ttk.Frame(self.root, padding=10)
        controls.pack(fill="x")

        ttk.Label(controls, text="Receiver port").grid(row=0, column=0, sticky="w")
        self.port_box = ttk.Combobox(controls, textvariable=self.port_var, width=22)
        self.port_box.grid(row=0, column=1, padx=5)
        ttk.Button(controls, text="Refresh", command=self.refresh_ports).grid(row=0, column=2)
        self.connect_button = ttk.Button(controls, text="Connect", command=self.toggle_serial)
        self.connect_button.grid(row=0, column=3, padx=5)

        ttk.Label(controls, text="Camera").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Spinbox(controls, from_=0, to=10, textvariable=self.camera_var, width=6).grid(
            row=1, column=1, sticky="w", padx=5
        )
        self.camera_button = ttk.Button(controls, text="Open Camera", command=self.toggle_camera)
        self.camera_button.grid(row=1, column=3, padx=5)

        ttk.Label(controls, text="Output folder").grid(row=2, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.output_var, width=45).grid(
            row=2, column=1, columnspan=2, padx=5, sticky="ew"
        )
        ttk.Button(controls, text="Browse", command=self.choose_output).grid(row=2, column=3)
        controls.columnconfigure(1, weight=1)

        self.preview = ttk.Label(self.root, text="Camera preview", anchor="center")
        self.preview.pack(fill="both", expand=True, padx=10, pady=5)

        actions = ttk.Frame(self.root, padding=10)
        actions.pack(fill="x")
        self.start_button = ttk.Button(actions, text="Start Recording", command=self.start_recording)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Stop", command=self.stop_recording, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Label(actions, textvariable=self.count_var).pack(side="right")
        ttk.Label(self.root, textvariable=self.status_var, padding=(10, 0, 10, 10)).pack(fill="x")

    def refresh_ports(self) -> None:
        ports = available_ports()
        self.port_box["values"] = ports
        if ports and self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def toggle_serial(self) -> None:
        if self.serial.is_connected:
            self.serial.disconnect()
            self.connect_button.configure(text="Connect")
            self.status_var.set("Receiver disconnected")
            return
        if not self.port_var.get():
            messagebox.showerror("Receiver", "Select a serial port")
            return
        try:
            self.serial.connect(self.port_var.get())
        except SerialReaderError as exc:
            messagebox.showerror("Receiver", str(exc))
            return
        self.connect_button.configure(text="Disconnect")
        self.status_var.set(f"Receiver connected on {self.serial.port}")

    def toggle_camera(self) -> None:
        if self.camera.is_open:
            self.camera.close()
            self.camera_button.configure(text="Open Camera")
            self.preview.configure(image="", text="Camera preview")
            return
        try:
            self.camera.open(
                self.camera_var.get(),
                self.config.camera_width,
                self.config.camera_height,
                self.config.camera_fps,
            )
        except CameraError as exc:
            messagebox.showerror("Camera", str(exc))
            return
        self.camera_button.configure(text="Close Camera")
        width, height = self.camera.frame_size
        self.status_var.set(
            f"Camera {self.camera.index} opened at {width}×{height}"
        )

    def choose_output(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_var.get())
        if selected:
            self.output_var.set(selected)

    def start_recording(self) -> None:
        if not self.camera.is_open or not self.serial.is_connected:
            messagebox.showerror("Not ready", "Open the camera and connect the receiver first")
            return
        self.serial.clear_buffer()
        try:
            session = self.recorder.start(
                Path(self.output_var.get()), self.camera.frame_size,
                self.config.video_fps, self.config.video_codec,
                self.camera.index or 0, self.serial.port or "",
                self.config.serial_baud,
            )
        except (OSError, RecorderError) as exc:
            messagebox.showerror("Recording", str(exc))
            return
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_var.set(f"Recording: {session.name}")

    def stop_recording(self) -> None:
        session = self.recorder.stop()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        if session:
            self.status_var.set(f"Saved: {session}")

    def _update(self) -> None:
        if self.camera.is_open:
            frame = self.camera.read()
            if frame is not None:
                captured_ns = time.monotonic_ns()
                self.recorder.write_frame(frame, captured_ns)
                preview = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                preview = Image.fromarray(preview)
                available_width = max(self.preview.winfo_width() - 20, 640)
                available_height = max(self.preview.winfo_height() - 20, 360)
                preview.thumbnail((available_width, available_height), Image.Resampling.LANCZOS)
                self.preview_image = ImageTk.PhotoImage(preview)
                self.preview.configure(image=self.preview_image, text="")

        while True:
            try:
                line = self.serial.lines.get_nowait()
            except Empty:
                break
            self.recorder.write_imu(line)

        self.count_var.set(
            f"Frames: {self.recorder.frame_count}   IMU samples: {self.recorder.imu_count}"
        )
        if self.serial.last_error:
            self.status_var.set(f"Serial error: {self.serial.last_error}")
        self.root.after(self.config.preview_interval_ms, self._update)

    def close(self) -> None:
        self.recorder.stop()
        self.serial.disconnect()
        self.camera.close()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    if root.winfo_screenwidth() >= 3000 or root.winfo_screenheight() >= 1800:
        root.geometry("1600x1200")
        root.minsize(1200, 900)
    else:
        root.geometry("1050x800")
        root.minsize(850, 650)
    RecorderApp(root)
    root.mainloop()
