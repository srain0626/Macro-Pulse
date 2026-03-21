import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from notifier import send_email_report, send_telegram_report


class NotifierTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_telegram_report_sends_message_and_images(self):
        with patch("notifier.Bot") as bot_cls, patch("notifier.os.path.exists", return_value=True), patch(
            "builtins.open", unittest.mock.mock_open(read_data=b"image")
        ):
            bot = AsyncMock()
            bot_cls.return_value = bot

            result = await send_telegram_report(
                "token",
                "chat-id",
                "hello",
                image_paths=["sample.png"],
                attempts=1,
            )

        self.assertTrue(result)
        bot.send_message.assert_awaited_once_with(chat_id="chat-id", text="hello")
        bot.send_photo.assert_awaited_once()

    def test_send_email_report_uses_smtp_context_manager(self):
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.__exit__.return_value = False

        with patch("notifier.smtplib.SMTP", return_value=smtp) as smtp_cls:
            result = send_email_report(
                "user@example.com",
                "password",
                "target@example.com",
                "<html>Report</html>",
            )

        self.assertTrue(result)
        smtp_cls.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("user@example.com", "password")
        smtp.sendmail.assert_called_once()
