# Human Acceptance Report — Jules Round 1

Date: 2026-09-25  
Repository: `scientifica007/Troika-D-Lite-J-01`  
Tested branch: `agent/build-v1-8166911284540142979`  
Tested commit: `be3dd26e778ab90d5a8787751b73b05b12f5e251`  
Environment: Ubuntu 24.04 LTS, Wayland desktop session

## Purpose

This document records the first real-machine human acceptance test of the Jules implementation. It preserves the Round 1 result before any repair work.

The original Jules submission branch and commit above are the reference baseline for Round 1.

## Automated test result

Command executed:

```bash
python3 -m unittest discover tests/
```

Observed result:

```text
...
----------------------------------------------------------------------
Ran 3 tests in 30.230s

OK
```

The tests passed, but they use `videotestsrc` / `audiotestsrc` in test mode. Therefore they validate pipeline construction and synthetic-media recording, not actual Wayland desktop capture.

## Human test results

### UI

PASS.

The GTK4 interface launches and is deliberately simple. It is practical for the Lite objective and exposes the required basic controls without unnecessary complexity.

Observed GTK/GSK warnings:

```text
Failed to realize renderer of type 'GskNglRenderer' ...
OpenGL ES 3.0 is not supported by this renderer.
```

These warnings did not prevent the application from launching or the controls from functioning.

### Audio-only recording

PASS in short manual tests.

The application successfully recorded:

- microphone only;
- system audio only;
- microphone + system audio.

Both internal and external microphones were usable.

The `Refresh Devices` control successfully refreshed the microphone list after an external microphone was connected. This is considered a useful low-overhead design choice for the Lite application.

All tested recordings were written as Matroska files (`.mkv`), including audio-only recordings. This is technically valid, though a future UX refinement may choose a dedicated audio extension/container if desired.

Long-duration continuity and drift have not yet been validated.

### Screen recording

FAIL — critical mandatory requirement.

When a screen recording mode was selected, the application did not record the desktop.

Instead, the resulting video captured the webcam.

This occurred with the current real pipeline based on:

```text
pipewiresrc ! videoconvert ! videorate ! ...
```

No desktop-selection portal dialog was observed during the tested screen-capture flow.

Therefore the following mandatory modes are not accepted in Round 1:

- video only;
- desktop video + system audio;
- desktop video + microphone;
- desktop video + system audio + microphone.

The audio branches can function, but the required desktop video source is incorrect.

## Code-review diagnosis

The current implementation treats bare `pipewiresrc` as if it were sufficient to obtain an authorized Wayland desktop stream.

The code does not implement the XDG Desktop Portal ScreenCast lifecycle needed for reliable Wayland desktop capture, such as:

- creating a ScreenCast session;
- selecting monitor/source types;
- starting the session and handling user authorization;
- receiving the returned PipeWire stream/node information;
- opening/using the authorized PipeWire remote;
- binding GStreamer capture to the selected desktop stream;
- closing the portal session cleanly.

This is the leading diagnosis for the webcam-vs-desktop failure and must be corrected rather than worked around by selecting an arbitrary PipeWire source.

## Stop/finalization concern from code review

The current stop path sends EOS and then waits only one second:

```python
bus.timed_pop_filtered(1 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)
```

It then forces the pipeline to `NULL`.

This is not yet accepted as robust finalization for slow hardware or long recordings. Repair work should wait for actual EOS asynchronously (with a bounded recovery timeout) and only tear down after muxer finalization, while keeping the UI responsive.

Repeated Start/Stop and long-duration file integrity still require real-machine validation.

## Diagnostics/testing gaps

Round 1 lacks enough diagnostics to investigate continuity problems if they occur. The original specification requested useful visibility into negotiated formats, selected sources, clocks, warnings/errors, QoS/drops and discontinuities where practical.

There is also no CI workflow on the tested commit.

The synthetic self-test does not currently prove:

- real XDG Portal integration;
- real PipeWire desktop capture;
- webcam exclusion;
- the full system-audio + microphone + desktop path;
- long-duration synchronization or continuity.

## Round 1 acceptance matrix

| Requirement | Result |
|---|---|
| Application launches | PASS |
| Simple/lightweight UI | PASS |
| Microphone-only recording | PASS (short test) |
| Internal microphone | PASS |
| External microphone | PASS |
| Refresh Devices | PASS |
| System-audio-only recording | PASS (short test) |
| Microphone + system audio | PASS (short test) |
| 15 / 30 FPS options exposed | PASS |
| Synthetic automated tests | PASS — 3/3 |
| Real Wayland desktop capture | **FAIL** |
| Video-only desktop recording | **FAIL** |
| Desktop + system audio | **FAIL** |
| Desktop + microphone | **FAIL** |
| Desktop + system + microphone | **FAIL** |
| Long-duration continuity | NOT YET VERIFIED |
| Robust EOS/finalization | NOT YET ACCEPTED |
| CPU/RAM target on old hardware | NOT YET MEASURED |
| Diagnostics | INSUFFICIENT |
| Round 1 Definition of Done | **NOT MET** |

## Round 1 conclusion

Jules produced a small, usable GTK4/GStreamer application with working short-test audio capture, including internal/external microphone handling, system audio, dual-source audio mixing, and manual device refresh.

However, the core mandatory screen-recording requirement failed human acceptance: the implementation captured the webcam instead of the Wayland desktop.

Round 1 must remain preserved at commit:

`be3dd26e778ab90d5a8787751b73b05b12f5e251`

Repair work should be performed on a new branch and should not rewrite or erase the Round 1 baseline.
