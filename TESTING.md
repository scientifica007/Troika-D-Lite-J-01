# Testing Procedures

## Automated Tests
Located in `tests/`. They verify:
- Logic for fetching available devices safely.
- Propagation of DBus Portal node ID into the pipeline generation.
- Complete asynchronous finalization and EOS bus message handling.
- A strong media self-test pipeline cycle that uses `videotestsrc` and multiple `audiotestsrc` elements to test the heavy mode (`video + system audio + mic`) without invoking a real Wayland portal.

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
