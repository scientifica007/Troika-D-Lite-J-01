# Known Limitations

- **Screen Selection Pre-view**: There is no live preview window for the recording to conserve resources on older hardware.
- **Hardware Encoding**: Exclusively uses software encoding (`x264enc`) optimized for speed. Hardware encoders (like VAAPI) are not utilized to avoid complex fallbacks and driver instability on varied hardware.
- **Microphone Hot-plugging**: The application does not automatically detect new microphones being plugged in. You must manually press the "Refresh Devices" button.
