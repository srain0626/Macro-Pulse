import os
import sys
import unittest


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from screenshot_utils import (
    take_finviz_screenshot,
    take_kosdaq_screenshot,
    take_kospi_screenshot,
)


@unittest.skipUnless(
    os.environ.get("RUN_SCREENSHOT_SMOKE_TESTS") == "1",
    "Set RUN_SCREENSHOT_SMOKE_TESTS=1 to exercise live screenshot capture.",
)
class ScreenshotSmokeTests(unittest.TestCase):
    def test_targets_can_capture_png(self):
        for target, capture in {
            "finviz": take_finviz_screenshot,
            "kospi": take_kospi_screenshot,
            "kosdaq": take_kosdaq_screenshot,
        }.items():
            with self.subTest(target=target):
                path = capture()
                try:
                    self.assertIsNotNone(path)
                    self.assertTrue(os.path.exists(path))
                finally:
                    if path and os.path.exists(path) and not os.environ.get(
                        "KEEP_TEST_ARTIFACTS"
                    ):
                        os.remove(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
