import os
import smtplib
from asyncio import sleep
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from telegram import Bot

from logging_utils import get_logger


logger = get_logger(__name__)


async def send_telegram_report(
    token,
    chat_id,
    message_text="Daily Macro Pulse Report",
    image_path=None,
    image_paths=None,
    attempts=2,
):
    """
    Sends the report to Telegram.
    Can send a message and/or an image.
    """
    if not token or not chat_id:
        logger.info("Telegram token or chat_id missing. Skipping Telegram.")
        return False

    photo_paths = []
    if image_paths:
        photo_paths.extend(image_paths)
    elif image_path:
        photo_paths.append(image_path)

    for attempt in range(1, attempts + 1):
        try:
            bot = Bot(token=token)
            await bot.send_message(chat_id=chat_id, text=message_text)

            for photo_path in photo_paths:
                if photo_path and os.path.exists(photo_path):
                    with open(photo_path, "rb") as img:
                        await bot.send_photo(chat_id=chat_id, photo=img)
                    logger.info("Telegram photo sent: %s", photo_path)

            return True
        except Exception as exc:
            logger.warning(
                "Failed to send Telegram message (attempt %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
            if attempt == attempts:
                logger.exception("Telegram delivery failed after retries")
                return False
            await sleep(1)


def send_email_report(smtp_user, smtp_password, recipient_email, html_content):
    """
    Sends the report via Email.
    """
    if not smtp_user or not smtp_password or not recipient_email:
        logger.info("SMTP credentials or recipient email missing. Skipping Email.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Daily Macro Pulse Report"
        msg["From"] = smtp_user
        msg["To"] = recipient_email

        part1 = MIMEText(html_content, "html")
        msg.attach(part1)

        # Standard Gmail SMTP port 587
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())
        logger.info("Email report sent.")
        return True
    except Exception as exc:
        logger.exception("Failed to send Email: %s", exc)
        return False
