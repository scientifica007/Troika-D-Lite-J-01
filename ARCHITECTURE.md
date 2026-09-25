# Architecture

Troika D Lite uses a Python GTK4 frontend and a GStreamer backend.

## Process Model
- Single-process application.
- UI runs on the main GLib loop.
- Media processing runs in GStreamer's internal threads.

## Screen Capture Path
Uses `pipewiresrc` mapped explicitly to a `path` (node ID) that is authorized by the XDG Desktop Portal (`org.freedesktop.portal.ScreenCast`). Troika D Lite implements a native asynchronous DBus client using `Gio.DBusProxy` to negotiate the session, select monitor sources, and retrieve the authorized PipeWire node ID before creating the GStreamer pipeline. This guarantees it captures the Wayland desktop, rather than falling back to an unprompted webcam. The frames are passed through `videoconvert` and `videorate` to enforce monotonic timestamps and the requested framerate.

## Audio Capture Path
Uses `pulsesrc` to capture audio. PulseAudio/Pipewire handles the device abstraction.
For microphones, it captures the default source. For system audio, it captures the monitor of the default sink.

## Synchronization Strategy
Both audio and video branches feed into an `audiomixer` (for audio streams) and `matroskamux` (for containerizing). Timestamps are generated monotonically by the sources. The queues are configured to prevent slow encoders from blocking the capture sources, prioritizing continuity.

## Buffering/Backpressure
Queues with generous bounds (e.g., 3 frames for video before encoding, and up to 10 buffers for mixed audio) are used to absorb scheduler jitter on older hardware, avoiding backpressure that might lead to dropped frames at the source.

## Encoder Strategy
- Video: `x264enc` with `speed-preset=ultrafast tune=zerolatency` for minimal CPU footprint and lowest latency.
- Audio: `avenc_aac` for reliable and standard audio encoding.

## Cleanup/Finalization
Stopping a recording asynchronously sends a GStreamer End-Of-Stream (EOS) event through the pipeline. The main application loop listens for the EOS confirmation message on the bus before transitioning the pipeline state to NULL and notifying the user. A 10-second bounded recovery timeout prevents the UI from freezing indefinitely if the muxer hangs during finalization. This ensures files are properly flushed and closed without blocking the GUI.
