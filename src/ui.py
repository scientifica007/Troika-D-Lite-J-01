import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
from .devices import get_audio_devices
from .recorder import Recorder, RecorderError
from .portal import ScreencastPortal
import os
import time

class TroikaApp(Gtk.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Troika D Lite")
        self.set_default_size(400, 500)

        self.recorder = Recorder()
        self.recorder.on_error_callback = self.on_recorder_error
        self.recorder.on_stop_callback = self.on_recorder_stopped
        self.start_time = 0
        self.timer_id = None

        self.portal = None

        self.build_ui()
        self.refresh_devices()

    def build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        self.set_child(vbox)

        # Recording Type
        vbox.append(Gtk.Label(label="Recording Type:"))
        self.type_combo = Gtk.DropDown.new_from_strings(["Screen Recording", "Audio Only"])
        vbox.append(self.type_combo)

        # FPS
        vbox.append(Gtk.Label(label="Frame Rate:"))
        self.fps_combo = Gtk.DropDown.new_from_strings(["30 FPS", "15 FPS"])
        vbox.append(self.fps_combo)

        # Audio Options
        vbox.append(Gtk.Label(label="Audio Options:"))
        self.audio_combo = Gtk.DropDown.new_from_strings([
            "No Audio",
            "Microphone",
            "System Audio",
            "System Audio + Microphone"
        ])
        vbox.append(self.audio_combo)

        # Microphone selector
        vbox.append(Gtk.Label(label="Microphone:"))
        self.mic_combo = Gtk.DropDown()
        vbox.append(self.mic_combo)

        # Refresh devices button
        refresh_btn = Gtk.Button(label="Refresh Devices")
        refresh_btn.connect("clicked", self.on_refresh_clicked)
        vbox.append(refresh_btn)

        # Output folder
        vbox.append(Gtk.Label(label="Output Folder:"))
        self.folder_entry = Gtk.Entry()
        self.folder_entry.set_text(os.path.expanduser("~/Videos"))
        vbox.append(self.folder_entry)

        # Status / Timer
        self.status_label = Gtk.Label(label="Ready")
        vbox.append(self.status_label)
        self.timer_label = Gtk.Label(label="00:00:00")
        vbox.append(self.timer_label)

        # Start/Stop Buttons
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hbox.set_halign(Gtk.Align.CENTER)
        vbox.append(hbox)

        self.start_btn = Gtk.Button(label="Start Recording")
        self.start_btn.connect("clicked", self.on_start_clicked)
        hbox.append(self.start_btn)

        self.stop_btn = Gtk.Button(label="Stop Recording")
        self.stop_btn.connect("clicked", self.on_stop_clicked)
        self.stop_btn.set_sensitive(False)
        hbox.append(self.stop_btn)

    def refresh_devices(self):
        self.devices = get_audio_devices()
        mic_devices = [d for d in self.devices if not d.is_monitor]
        strings = [d.description for d in mic_devices]

        if not strings:
            strings = ["No microphone found"]

        self.mic_model = Gtk.StringList.new(strings)
        self.mic_combo.set_model(self.mic_model)
        self.mic_devices_map = mic_devices

    def on_refresh_clicked(self, btn):
        self.refresh_devices()

    def update_timer(self):
        if not self.recorder.is_recording:
            return False

        elapsed = int(time.time() - self.start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.timer_label.set_text(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        return True

    def on_start_clicked(self, btn):
        rec_type_idx = self.type_combo.get_selected()
        record_type = "screen" if rec_type_idx == 0 else "audio_only"

        fps_idx = self.fps_combo.get_selected()
        fps = 30 if fps_idx == 0 else 15

        audio_idx = self.audio_combo.get_selected()
        audio_map = {
            0: "no_audio",
            1: "mic",
            2: "system_audio",
            3: "system_and_mic"
        }
        audio_option = audio_map.get(audio_idx, "no_audio")

        if record_type == "audio_only" and audio_option == "no_audio":
            self.status_label.set_text("Error: Cannot record Audio Only with No Audio selected.")
            return

        mic_idx = self.mic_combo.get_selected()
        selected_mic = None
        if mic_idx < len(self.mic_devices_map):
            selected_mic = self.mic_devices_map[mic_idx]

        output_folder = self.folder_entry.get_text()

        self.start_btn.set_sensitive(False)
        self.status_label.set_text("Starting...")

        if record_type == "screen":
            # Initiate Portal flow
            try:
                self.portal = ScreencastPortal()
                self.portal.request_screencast(
                    lambda node_id, fd: self._start_recording_internal(record_type, fps, audio_option, selected_mic, output_folder, str(node_id), fd),
                    self._on_portal_cancel
                )
            except Exception as e:
                self.status_label.set_text(f"Portal error: {e}")
                self.start_btn.set_sensitive(True)
        else:
            self._start_recording_internal(record_type, fps, audio_option, selected_mic, output_folder, None, None)

    def _on_portal_cancel(self, msg):
        self.status_label.set_text(f"Portal cancelled: {msg}")
        self.start_btn.set_sensitive(True)
        if self.portal:
            self.portal.cleanup()
            self.portal = None

    def _start_recording_internal(self, record_type, fps, audio_option, selected_mic, output_folder, node_id, fd):
        try:
            self.recorder.start_recording(record_type, fps, audio_option, selected_mic, output_folder, node_id, fd)
            self.stop_btn.set_sensitive(True)
            self.status_label.set_text("Recording...")

            self.start_time = time.time()
            self.timer_id = GLib.timeout_add_seconds(1, self.update_timer)

        except RecorderError as e:
            self.status_label.set_text(f"Error: {e}")
            self.start_btn.set_sensitive(True)
            if self.portal:
                self.portal.cleanup()
                self.portal = None

    def on_recorder_error(self, err_msg):
        self.start_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)
        self.status_label.set_text(f"Error: {err_msg}")
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        if self.portal:
            self.portal.cleanup()
            self.portal = None

    def on_recorder_stopped(self):
        self.start_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)
        self.status_label.set_text("Saved to " + str(self.recorder.output_file))
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = None
        if self.portal:
            self.portal.cleanup()
            self.portal = None

    def on_stop_clicked(self, btn):
        self.stop_btn.set_sensitive(False)
        self.status_label.set_text("Finalizing recording...")
        self.recorder.stop_recording()
