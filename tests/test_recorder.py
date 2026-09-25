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

    def test_record_cycle(self):
        # We can try to run a brief 1-second recording in test mode
        mic = AudioDevice("fake_mic", "Fake Mic", False)
        output_file = self.recorder.start_recording('screen', 15, 'mic', mic, self.temp_dir)
        self.assertTrue(self.recorder.is_recording)
        self.assertIsNotNone(self.recorder.pipeline)

        time.sleep(1) # Let it process some frames

        self.recorder.stop_recording()
        self.assertFalse(self.recorder.is_recording)
        self.assertIsNone(self.recorder.pipeline)

        self.assertTrue(os.path.exists(output_file))
        size = os.path.getsize(output_file)
        self.assertGreater(size, 0)

        os.remove(output_file)
        os.rmdir(self.temp_dir)
