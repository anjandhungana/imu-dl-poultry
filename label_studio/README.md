# Label Studio behavioral labeling

This configuration displays the recorded video and six IMU channels on one synchronized timeline. Labels are applied to selected time ranges on the IMU plot.

The synchronized template requires Label Studio 1.20 or newer.

## 1. Prepare recorded sessions

From `imu-video-recorder`:

```bash
.venv/bin/python label_studio/prepare_tasks.py
```

This creates `label_studio/tasks.json`, converted time-series CSV files, and browser-compatible H.264 video copies under `label_studio/processed`. The original recordings are not modified. Run it again whenever new sessions are recorded.

## 2. Start the media server

```bash
.venv/bin/python label_studio/serve_files.py
```

Keep that terminal open while labeling. The server runs at `http://127.0.0.1:8765`, supplies browser-compatible CORS headers, and does not affect Label Studio accounts.

## 3. Start Label Studio

If `label-studio` is already installed:

```bash
chmod +x label_studio/start_label_studio.sh
./label_studio/start_label_studio.sh
```

Open <http://localhost:8080> and sign in or create the local account when prompted.

The launcher uses Label Studio's normal data directory, so an existing local account and projects remain available. Local-file serving does not require a separate account.

You can start Label Studio normally. Local-file serving does not need to be enabled when using the media server.

## 4. Create the project

1. Create a project named **Behavior Classification**.
2. Open **Settings → Labeling Interface → Code**.
3. Copy the complete contents of `label_studio/label_config.xml`, save, and verify the preview.
4. Return to the project and import `label_studio/tasks.json`.
5. Open a task. The video and IMU playhead should move together.

Do not use **Cloud Storage → Sync** for this workflow. The prepared JSON already groups each session's video and IMU CSV into one task.

## Labels

The starter labels are Standing, Walking, Running, Sitting, Lying, Transition, and Other. Edit the `<Label>` entries in `label_config.xml` before beginning production annotations if your behavioral taxonomy differs.

## Labeling

1. Play or seek the video to identify a behavior.
2. Choose its label or press the displayed number hotkey.
3. Drag across the corresponding interval in the IMU timeline.
4. Cover the recording with non-overlapping regions and submit the task.

The source recordings are never modified. Only converted timeline CSV files and Label Studio's own annotation database are written.
