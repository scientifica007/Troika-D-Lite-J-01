import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
from datetime import datetime

class RecorderError(Exception):
    pass

class Recorder:
    def __init__(self):
        # We only initialize Gst once
        if not Gst.is_initialized():
            Gst.init(None)

        self.pipeline = None
        self.output_file = None
        self.is_recording = False

        # Test mode for headless CI
        self.test_mode = False

    def build_pipeline_string(self, record_type, fps, audio_option, mic_device, output_path):
        """
        Builds the GStreamer pipeline string dynamically based on requirements.
        - record_type: 'audio_only' or 'screen'
        - fps: 15 or 30
        - audio_option: 'no_audio', 'system_audio', 'mic', 'system_and_mic'
        """
        pipeline_parts = []

        has_video = (record_type == 'screen')
        has_mic = (audio_option in ['mic', 'system_and_mic'])
        has_system = (audio_option in ['system_audio', 'system_and_mic'])

        # For simplicity and efficiency on older devices, use matroskamux and software encoders.
        # x264enc speed-preset=ultrafast tune=zerolatency for very fast encoding.
        # avenc_aac for audio.
        # Muxer is matroskamux (mkv).

        muxer_part = f'matroskamux name=mux ! filesink location="{output_path}"'
        pipeline_parts.append(muxer_part)

        if has_video:
            if self.test_mode:
                video_src = f"videotestsrc ! video/x-raw,framerate={fps}/1"
            else:
                video_src = f"pipewiresrc ! videoconvert ! videorate ! video/x-raw,framerate={fps}/1"

            video_enc = f"{video_src} ! queue max-size-buffers=3 ! x264enc speed-preset=ultrafast tune=zerolatency key-int-max={fps} threads=2 ! h264parse ! queue ! mux."
            pipeline_parts.append(video_enc)

        if has_mic or has_system:
            pipeline_parts.append("audiomixer name=mix ! queue max-size-buffers=10 ! audioconvert ! avenc_aac ! queue ! mux.")

            if has_mic:
                if self.test_mode:
                    mic_src = "audiotestsrc wave=sine freq=440"
                else:
                    device = mic_device.name if mic_device else "default"
                    mic_src = f"pulsesrc device={device}"

                pipeline_parts.append(f"{mic_src} ! queue max-size-time=1000000000 ! audioconvert ! audioresample ! mix.")

            if has_system:
                if self.test_mode:
                    sys_src = "audiotestsrc wave=sine freq=880"
                else:
                    sys_src = "pulsesrc device=@DEFAULT_MONITOR@"

                pipeline_parts.append(f"{sys_src} ! queue max-size-time=1000000000 ! audioconvert ! audioresample ! mix.")

        return " ".join(pipeline_parts)

    def start_recording(self, record_type, fps, audio_option, mic_device, output_folder):
        if self.is_recording:
            raise RecorderError("Already recording")

        # Ensure output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_file = os.path.join(output_folder, f"Troika-D-Lite_{timestamp}.mkv")

        pipeline_str = self.build_pipeline_string(record_type, fps, audio_option, mic_device, self.output_file)

        print("Pipeline:", pipeline_str)
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            raise RecorderError(f"Failed to create pipeline: {e}")

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)

        ret = self.pipeline.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            raise RecorderError("Failed to start pipeline")

        self.is_recording = True
        return self.output_file

    def stop_recording(self):
        if not self.is_recording or not self.pipeline:
            return

        # Send EOS to finalize the file properly
        self.pipeline.send_event(Gst.Event.new_eos())

        # Wait for EOS on bus, but don't block indefinitely if we are just shutting down cleanly
        # However, for a UI app it's better not to block here at all,
        # but rather let the on_message handler handle EOS and cleanup.
        # But to satisfy the immediate "stop" requirement in the simplest way without freezing,
        # we do a very short poll or just rely on bus messages.

        # Wait up to 1 second for EOS
        bus = self.pipeline.get_bus()
        bus.timed_pop_filtered(1 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)

        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None
        self.is_recording = False

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            self.is_recording = False

            # Use GLib to dispatch the error callback to the main thread if it exists
            if hasattr(self, 'on_error_callback') and self.on_error_callback:
                GLib.idle_add(self.on_error_callback, str(err))

        elif t == Gst.MessageType.EOS:
            print("End-Of-Stream reached.")
