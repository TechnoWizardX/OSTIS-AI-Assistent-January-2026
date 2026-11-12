import os
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.network_monitor import NetworkChecker
from src.modules.gesture import gestures


class ShutdownTests(unittest.TestCase):
    def test_network_checker_stop_interrupts_interval_wait(self):
        check_started = threading.Event()

        def check():
            check_started.set()
            return False

        with patch.object(NetworkChecker, "_check", side_effect=check):
            checker = NetworkChecker(interval=60)
            checker.start()
            self.assertTrue(check_started.wait(timeout=2))

            started_at = time.monotonic()
            checker.stop()

            self.assertLess(time.monotonic() - started_at, 1)
            self.assertFalse(checker.isRunning())

    def test_camera_open_failure_releases_camera_and_processor(self):
        capture = Mock()
        capture.isOpened.return_value = False
        processor = Mock()

        with (
            patch.object(gestures, "GestureProcessor", return_value=processor),
            patch.object(gestures.cv2, "VideoCapture", return_value=capture),
        ):
            camera_thread = gestures.GestureCameraThread()
            camera_thread.run()

        capture.release.assert_called_once()
        processor.shutdown.assert_called_once()
        self.assertIsNone(camera_thread.cap)
        self.assertIsNone(camera_thread.processor)


if __name__ == "__main__":
    unittest.main()
