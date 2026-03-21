import asyncio
import os
import sys
import unittest

from dotenv import load_dotenv


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from data_fetcher import fetch_all_data
from notifier import send_telegram_report
from report_generator import generate_html_report


load_dotenv()


@unittest.skipUnless(
    os.environ.get("RUN_LIVE_SMOKE_TESTS") == "1",
    "Set RUN_LIVE_SMOKE_TESTS=1 to run the live end-to-end smoke test.",
)
class EndToEndSmokeTests(unittest.TestCase):
    def test_live_report_pipeline(self):
        async def _run():
            data = fetch_all_data()
            self.assertTrue(any(data.values()))

            html_content = generate_html_report(data)
            self.assertIn("Macro Pulse Daily Report", html_content)

            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID")
            if token and chat_id:
                result = await send_telegram_report(
                    token,
                    chat_id,
                    message_text="[E2E Test] Macro Pulse Report",
                )
                self.assertTrue(result)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
