# IMU + Video Recorder

A small desktop application that records webcam video and ESP-NOW receiver data on one computer timeline.

## Setup

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

## Test workflow

1. Flash and connect the ESP32-S3 USB-OTG receiver.
2. Start the XIAO ESP32-C3 transmitter and wait until it reports `streaming=yes`.
3. Run the application.
4. Select the receiver port and click **Connect**.
5. Click **Open Camera** and confirm the preview.
6. Choose an output folder.
7. Click **Start Recording**. Earlier serial packets are discarded.
8. Click **Stop** to finish and save the session.

Each session contains:

- `video.mp4` — recorded webcam video
- `imu.csv` — IMU samples with computer-relative timestamps
- `video_frames.csv` — frame-to-time mapping
- `session.json` — recording metadata and counts

Receiver diagnostic lines beginning with `#` are ignored automatically.

## Behavioral labeling

See [label_studio/README.md](label_studio/README.md) for the synchronized video and IMU labeling workflow.
