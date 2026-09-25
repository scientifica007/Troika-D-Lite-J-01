import unittest
import os
import tempfile
import time
from src.recorder import Recorder, RecorderError
from src.devices import AudioDevice

class TestRecorder(unittest.TestCase):
    def setUp(self):
        self.recorder = Recorder()
        self.recorder.test_mode = True # Use videotestsrc and audiotestsrc
        self.temp_dir = tempfile.mkdtemp()

    def test_pipeline_construction(self):
        mic = AudioDevice("fake_mic", "Fake Mic", False)

        # Test 1: Video + Mic
        pipe_str = self.recorder.build_pipeline_string('screen', 30, 'mic', mic, '/tmp/out.mkv')
        self.assertIn('matroskamux name=mux ! filesink', pipe_str)
        self.assertIn('videotestsrc ! video/x-raw,framerate=30/1', pipe_str)
        self.assertIn('audiotestsrc wave=sine freq=440', pipe_str)

        # Test 2: Audio Only
        pipe_str2 = self.recorder.build_pipeline_string('audio_only', 30, 'system_audio', None, '/tmp/out2.mkv')
        self.assertNotIn('videotestsrc', pipe_str2)
        self.assertIn('audiotestsrc wave=sine freq=880', pipe_str2)

        # Test 3: Video + Mic + System Audio (Heavy Mode) + node_id
        pipe_str3 = self.recorder.build_pipeline_string('screen', 15, 'system_and_mic', mic, '/tmp/out3.mkv', '99')
        self.assertIn('videotestsrc', pipe_str3) # test mode overrides pipewiresrc, but we test the signature
        self.assertIn('wave=sine freq=440', pipe_str3)
        self.assertIn('wave=sine freq=880', pipe_str3)

        # Test 4: Verify node_id propagation in production mode
        self.recorder.test_mode = False
        pipe_str4 = self.recorder.build_pipeline_string('screen', 15, 'mic', mic, '/tmp/out4.mkv', '100', 42)
        self.assertIn('pipewiresrc path=100 fd=42 ! videoconvert', pipe_str4)

    def test_record_cycle(self):
        # We can try to run a brief 1-second recording in test mode
        mic = AudioDevice("fake_mic", "Fake Mic", False)
        output_file = self.recorder.start_recording('screen', 15, 'system_and_mic', mic, self.temp_dir)
        self.assertTrue(self.recorder.is_recording)
        self.assertIsNotNone(self.recorder.pipeline)

        time.sleep(1) # Let it process some frames

        # Stop now uses an asynchronous EOS event handling or fallback timeout
        self.recorder.stop_recording()

        # Wait a little bit for the bus message to be processed
        # (in real app, GLib main loop handles it, here we might need to manually poll bus or just wait)
        import gi
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        bus = self.recorder.pipeline.get_bus()
        bus.timed_pop_filtered(2 * Gst.SECOND, Gst.MessageType.EOS | Gst.MessageType.ERROR)

        # Manually invoke the callback since GLib main loop isn't running in this simple unittest
        msg = Gst.Message.new_eos(self.recorder.pipeline)
        self.recorder.on_message(bus, msg)

        self.assertFalse(self.recorder.is_recording)
        self.assertIsNone(self.recorder.pipeline)

        self.assertTrue(os.path.exists(output_file))
        size = os.path.getsize(output_file)
        self.assertGreater(size, 0)

        os.remove(output_file)
        os.rmdir(self.temp_dir)
