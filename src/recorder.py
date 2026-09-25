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

    def build_pipeline_string(self, record_type, fps, audio_option, mic_device, output_path, node_id=None, fd=None):
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
                pw_path = f"path={node_id}" if node_id else ""
                pw_fd = f"fd={fd}" if fd and fd != -1 else ""
                video_src = f"pipewiresrc {pw_path} {pw_fd} ! videoconvert ! videorate ! video/x-raw,framerate={fps}/1"

            bitrate = 4000 if fps == 15 else 6000
            video_enc = f"{video_src} ! queue max-size-buffers=3 ! x264enc speed-preset=ultrafast tune=zerolatency bitrate={bitrate} key-int-max={fps} threads=2 ! h264parse ! queue ! mux."
            pipeline_parts.append(video_enc)

        if has_mic or has_system:
            # Enlarge queue after audiomixer to 3 seconds to prevent encoder/muxer backpressure from dropping mic frames.
            pipeline_parts.append("audiomixer name=mix ! queue max-size-time=3000000000 max-size-bytes=0 max-size-buffers=0 ! audioconvert ! avenc_aac ! queue ! mux.")

            if has_mic:
                if self.test_mode:
                    mic_src = "audiotestsrc wave=sine freq=440 is-live=true"
                else:
                    device = mic_device.name if mic_device else "default"
                    # Add do-timestamp=true so pulsesrc aligns with the pipeline clock accurately.
                    mic_src = f"pulsesrc device={device} do-timestamp=true"

                pipeline_parts.append(f"{mic_src} ! queue max-size-time=1000000000 ! audioconvert ! audioresample ! mix.")

            if has_system:
                if self.test_mode:
                    sys_src = "audiotestsrc wave=sine freq=880 is-live=true"
                else:
                    sys_src = "pulsesrc device=@DEFAULT_MONITOR@ do-timestamp=true"

                pipeline_parts.append(f"{sys_src} ! queue max-size-time=1000000000 ! audioconvert ! audioresample ! mix.")

        return " ".join(pipeline_parts)

    def start_recording(self, record_type, fps, audio_option, mic_device, output_folder, node_id=None, fd=None):
        if self.is_recording:
            raise RecorderError("Already recording")

        # Ensure output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_file = os.path.join(output_folder, f"Troika-D-Lite_{timestamp}.mkv")

        pipeline_str = self.build_pipeline_string(record_type, fps, audio_option, mic_device, self.output_file, node_id, fd)

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

        # Do not block here. We will handle EOS in on_message.
        # Start a fallback timeout just in case EOS never comes
        self._stop_timeout_id = GLib.timeout_add_seconds(10, self._force_stop)

    def _force_stop(self):
        print("EOS timeout reached, forcing pipeline to NULL.")
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
        self.is_recording = False

        if hasattr(self, 'on_stop_callback') and self.on_stop_callback:
            GLib.idle_add(self.on_stop_callback)

        return False # don't repeat timeout

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")

            if hasattr(self, '_stop_timeout_id'):
                GLib.source_remove(self._stop_timeout_id)
                del self._stop_timeout_id

            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            self.is_recording = False

            # Use GLib to dispatch the error callback to the main thread if it exists
            if hasattr(self, 'on_error_callback') and self.on_error_callback:
                GLib.idle_add(self.on_error_callback, str(err))

        elif t == Gst.MessageType.EOS:
            print("End-Of-Stream reached.")
            if hasattr(self, '_stop_timeout_id'):
                GLib.source_remove(self._stop_timeout_id)
                del self._stop_timeout_id

            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            self.is_recording = False

            if hasattr(self, 'on_stop_callback') and self.on_stop_callback:
                GLib.idle_add(self.on_stop_callback)
