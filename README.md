# Troika D Lite

A lightweight, reliable screen and audio recorder for Ubuntu Wayland.

## Features
- Screen capture via Wayland XDG Desktop Portal & PipeWire.
- Audio capture via PulseAudio/Pipewire for system audio and microphone.
- Supports Video only, Audio only, Video + Mic, Video + System Audio, and Video + System Audio + Mic.
- 15 FPS or 30 FPS.
- Low resource usage designed for older hardware.

## Installation

### Dependencies
Ensure you have the required GStreamer and GTK4 packages.
```bash
sudo apt-get update
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-4.0 \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-pipewire \
    gstreamer1.0-libav \
    pulseaudio-utils
```

### Setup & Run
Simply run the python main script:
```bash
python3 -m src.main
```

## Usage
1. Select Recording Type (Screen or Audio Only)
2. Set FPS (15 or 30)
3. Select Audio Options (No Audio, Microphone, System Audio, System Audio + Microphone)
4. Choose Microphone if applicable.
5. Click Start Recording. If it's a screen recording, a Wayland desktop portal window will prompt you to share your screen.
6. Click Stop Recording to finish. Output is saved to the designated folder.