import unittest
from src.devices import get_audio_devices, AudioDevice

class TestDevices(unittest.TestCase):
    def test_get_audio_devices(self):
        devices = get_audio_devices()
        self.assertIsInstance(devices, list)
        if devices:
            self.assertIsInstance(devices[0], AudioDevice)
            self.assertTrue(hasattr(devices[0], 'name'))
            self.assertTrue(hasattr(devices[0], 'is_monitor'))
