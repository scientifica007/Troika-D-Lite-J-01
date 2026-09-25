# Testing Procedures

## Automated Tests
Located in `tests/`. They verify:
- Logic for fetching available devices without failing.
- Construction of GStreamer pipelines based on the parameters (mode, fps, etc.).
- A self-test pipeline cycle that uses `videotestsrc` and `audiotestsrc` to simulate a recording session without invoking a real Wayland portal.

Run with:
```bash
python3 -m unittest discover tests/
```

## Real Wayland Test Procedure
1. Launch application in an Ubuntu 24.04 Wayland session.
2. Select Screen Recording + 15 FPS + System Audio + Microphone.
3. Start Recording, authorize the Wayland screen cast dialog.
4. Speak into the microphone while playing a video locally.
5. Stop recording.
6. Play the generated `.mkv` file. Validate that video is smooth, both audio sources are present, and there is no sync drift.

## Long-Recording Test Procedure
1. Follow above steps, but run for 20 minutes continuously.
2. Observe system monitor to ensure RAM remains stable (no memory leaks).
3. Ensure final file writes correctly upon Stop.
