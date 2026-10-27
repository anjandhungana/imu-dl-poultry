# Working Label Studio setup

This is the confirmed working setup for labeling synchronized behavioral video and raw IMU recordings.

## File arrangement

Each recorder session contains:

```text
recordings/session_YYYYMMDD_HHMMSS/
├── video.mp4
├── imu.csv
├── video_frames.csv
└── session.json
```

Label Studio reads the original `imu.csv`. The preparation script creates an H.264 copy of `video.mp4` because the original OpenCV `mp4v` recording is not reliably supported by web browsers.

## Prepare tasks

Run this after recording new sessions:

```bash
cd /home/anjandhungana_sp/Desktop/body-mounted-sensor-study/imu-video-recorder
.venv/bin/python label_studio/prepare_tasks.py
```

This creates or updates:

```text
label_studio/tasks.json
label_studio/processed/session_*/video.mp4
```

The task must reference the raw IMU file and processed H.264 video:

```json
[
  {
    "data": {
      "video": "http://127.0.0.1:8765/label_studio/processed/session_YYYYMMDD_HHMMSS/video.mp4",
      "imu": "http://127.0.0.1:8765/recordings/session_YYYYMMDD_HHMMSS/imu.csv"
    }
  }
]
```

## Start the media server

Run this before opening a labeling task and keep the terminal open:

```bash
cd /home/anjandhungana_sp/Desktop/body-mounted-sensor-study/imu-video-recorder
.venv/bin/python label_studio/serve_files.py
```

Expected output:

```text
Serving ... at http://127.0.0.1:8765
```

This server provides the required CORS headers. Label Studio local-file serving does not need to be enabled.

## Labeling interface

Paste this into **Project → Settings → Labeling Interface → Code**:

```xml
<View>
  <Header value="Behavior Classification"/>

  <TimeSeriesLabels name="behavior" toName="imu" choice="single">
    <Label value="Standing" background="#4C78A8" hotkey="1"/>
    <Label value="Walking" background="#59A14F" hotkey="2"/>
    <Label value="Running" background="#F28E2B" hotkey="3"/>
    <Label value="Sitting" background="#B279A2" hotkey="4"/>
    <Label value="Lying" background="#76B7B2" hotkey="5"/>
    <Label value="Transition" background="#EDC948" hotkey="6"/>
    <Label value="Other" background="#BAB0AC" hotkey="7"/>
  </TimeSeriesLabels>

  <Video
    name="video"
    value="$video"
    sync="recording"
    frameRate="30"
    height="420"
  />

  <Header value="Acceleration and angular velocity"/>
  <TimeSeries
    name="imu"
    value="$imu"
    valueType="url"
    sync="recording"
    sep=","
    timeColumn="elapsed_time_s"
    timeDisplayFormat=".2f"
    durationDisplayFormat=".2f"
    overviewChannels="ax,ay,az"
    overviewWidth="12%"
    fixedScale="true">

    <MultiChannel height="240">
      <Channel column="ax" legend="Accel X" units="m/s²" strokeColor="#E15759"/>
      <Channel column="ay" legend="Accel Y" units="m/s²" strokeColor="#59A14F"/>
      <Channel column="az" legend="Accel Z" units="m/s²" strokeColor="#4E79A7"/>
    </MultiChannel>

    <MultiChannel height="240">
      <Channel column="gx" legend="Gyro X" units="rad/s" strokeColor="#F28E2B"/>
      <Channel column="gy" legend="Gyro Y" units="rad/s" strokeColor="#B07AA1"/>
      <Channel column="gz" legend="Gyro Z" units="rad/s" strokeColor="#76B7B2"/>
    </MultiChannel>
  </TimeSeries>
</View>
```

The critical setting for the raw recorder CSV is:

```xml
timeColumn="elapsed_time_s"
```

## Import tasks

1. Delete obsolete tasks that referenced `/data/local-files/` or converted IMU CSV files.
2. Click **Import** in the Label Studio project.
3. Import `label_studio/tasks.json`.
4. Keep the media-server terminal running while labeling.

## Errors resolved by this setup

### Video format is not supported

The raw OpenCV video uses MPEG-4 Part 2 (`mp4v`). `prepare_tasks.py` creates an H.264 copy for the browser.

### `URL_CORS_DOCS` error

Use `serve_files.py` rather than Label Studio local-file serving. It provides the required media URLs and CORS headers without changing Label Studio authentication or its database.

### `Cannot read properties of undefined (reading '0')`

This occurred when the interface requested `elapsed_time_s` but the task referenced a converted CSV containing a column called `time`. The working task references the raw `imu.csv`, whose time column is `elapsed_time_s`.
