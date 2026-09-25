# Human Acceptance Report — Jules Working Wayland Baseline

Date: 2026-09-25  
Repository: `scientifica007/Troika-D-Lite-J-01`  
Tested Jules branch: `agent/build-v1-8166911284540142979`  
Tested commit: `68320c41cd51eb669a34b2f4cbace9ec6d5ddc76`  
Environment: Ubuntu 24.04 LTS, Wayland desktop session

## Summary

This human test establishes the first Jules build that successfully records the actual Wayland desktop through the XDG Desktop Portal + PipeWire path.

The Portal repair is therefore considered functionally successful on the human test machine.

Do not regress or unnecessarily redesign the working Portal integration in subsequent tuning work.

## Automated tests

Observed:

```text
Ran 4 tests in 1.309s
OK
```

## Wayland ScreenCast

PASS.

Observed real sequence:

```text
CreateSession-build
CreateSession-call
SelectSources-build
SelectSources-call
Start-build
Start-call
OpenPipeWireRemote
Pipeline: ... pipewiresrc path=<node> fd=<fd> ...
```

The system screen-sharing dialog appeared and the built-in display could be selected.

The resulting recordings contain the desktop rather than the webcam.

This is a material improvement over the Round 1 implementation.

## Recording modes exercised

Real-machine testing included combinations of:

- screen only;
- 15 FPS;
- 30 FPS;
- screen + internal microphone;
- screen + external USB microphone;
- screen + system audio;
- screen + microphone + system audio;
- audio-only microphone/system combinations.

EOS completion was observed repeatedly in the terminal after short recordings.

## Audio findings

### Audio-only recording

PASS.

Microphone recording without video is good.

This strongly indicates that the microphone capture path itself is fundamentally functional.

System audio is also good.

### Screen + microphone

PARTIAL / FAIL FOR CONTINUITY.

When video recording is active with microphone audio, microphone audio exhibits frequent interruptions/dropouts.

This occurs despite microphone-only recording being good.

Therefore the defect is currently localized to the interaction between the video branch and microphone branch, rather than basic microphone acquisition.

### Screen + microphone + system audio

At 15 FPS, microphone interruptions become much less frequent and may be nearly absent in short tests.

System audio remains good.

This behavior is diagnostically important and should be investigated before changing microphone parameters blindly.

## Video findings

Desktop capture works, but image quality is currently poor.

Current video encoding uses approximately:

```text
x264enc speed-preset=ultrafast tune=zerolatency
```

The implementation should improve visual quality without losing the original low-resource objective for old hardware.

Do not introduce heavy rendering, preview, or large framework dependencies.

## Current acceptance state

| Requirement | Result |
|---|---|
| GTK4 application launches | PASS |
| Real XDG Portal dialog | PASS |
| Real Wayland desktop capture | PASS |
| 15 FPS desktop capture | PASS |
| 30 FPS desktop capture | PASS |
| Audio-only microphone | PASS |
| Audio-only system audio | PASS |
| Internal microphone | PASS |
| External USB microphone | PASS |
| Refresh Devices | PASS |
| System audio with screen | PASS |
| Screen + microphone continuity | FAIL / unstable |
| Screen + mic + system at 15 FPS | Much improved in short test |
| Video image quality | FAIL / poor |
| Repeated short EOS finalization | PASS in observed tests |
| Long-duration test | NOT YET PERFORMED |
| CPU/RAM target | NOT YET MEASURED |

## Next engineering priorities

1. Diagnose microphone dropouts specifically when video is present.
2. Do not modify the working Portal integration unless a direct defect is demonstrated.
3. Preserve the good audio-only path as a control/baseline.
4. Compare:
   - mic only;
   - screen 15 + mic;
   - screen 30 + mic;
   - screen 15 + system + mic;
   - screen 30 + system + mic.
5. Add diagnostics for:
   - pipeline clock;
   - latency messages;
   - discontinuities;
   - QoS/dropped buffers;
   - queue/backpressure where practical;
   - actual audio source buffering.
6. Only after audio continuity is stabilized, improve video quality with the smallest practical CPU cost.
7. After short tests are stable, perform a 20-minute acceptance recording.

## Important constraint

The working Wayland path at commit:

`68320c41cd51eb669a34b2f4cbace9ec6d5ddc76`

is now a valuable functional baseline.

Future work should preserve this behavior.
