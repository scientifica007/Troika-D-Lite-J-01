# Architecture

Troika D Lite uses a Python GTK4 frontend and a GStreamer backend.

## Process Model
- Single-process application.
- UI runs on the main GLib loop.
- Media processing runs in GStreamer's internal threads.

## Screen Capture Path
Uses `pipewiresrc` mapped explicitly to a `path` (node ID) that is authorized by the XDG Desktop Portal (`org.freedesktop.portal.ScreenCast`). Troika D Lite implements a native asynchronous DBus client using `Gio.DBusProxy` to negotiate the session, select monitor sources, and retrieve the authorized PipeWire node ID and file descriptor before creating the GStreamer pipeline. This guarantees it captures the Wayland desktop, rather than falling back to an unprompted webcam. The frames are passed through `videoconvert` and `videorate` to enforce monotonic timestamps and the requested framerate.

## Audio Capture Path
Uses `pulsesrc` to capture audio. PulseAudio/Pipewire handles the device abstraction.
For microphones, it captures the default source. For system audio, it captures the monitor of the default sink.

## Synchronization Strategy
Both audio and video branches feed into an `audiomixer` (for audio streams) and `matroskamux` (for containerizing). Timestamps are generated monotonically by the sources. The queues are configured to prevent slow encoders from blocking the capture sources, prioritizing continuity.

## Buffering/Backpressure
Queues with generous bounds are used to absorb scheduler jitter on older hardware, avoiding backpressure that might lead to dropped frames at the source.
Specifically, the queue after the `audiomixer` and before the muxer was significantly enlarged (up to 3 seconds `max-size-time`) because earlier 10-buffer sizes caused audio dropouts when combined with heavy video encoding. Additionally, `do-timestamp=true` is used on `pulsesrc` so live audio correctly aligns with the pipeline clock even if processing is momentarily delayed.

## Encoder Strategy
- Video: `x264enc` with `speed-preset=ultrafast tune=zerolatency` to guarantee low CPU footprint on older hardware. We set a bitrate limit explicitly (4000 kbps for 15 FPS, 6000 kbps for 30 FPS) to balance visual quality without overwhelming the encoder and causing backpressure on the capture queues.
- Audio: `avenc_aac` for reliable and standard audio encoding.

## Cleanup/Finalization
Stopping a recording asynchronously sends a GStreamer End-Of-Stream (EOS) event through the pipeline. The main application loop listens for the EOS confirmation message on the bus before transitioning the pipeline state to NULL and notifying the user. A 10-second bounded recovery timeout prevents the UI from freezing indefinitely if the muxer hangs during finalization. This ensures files are properly flushed and closed without blocking the GUI.
