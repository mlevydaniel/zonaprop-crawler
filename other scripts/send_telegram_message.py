import requests
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(bot_token, chat_id, message):
    """
    Send a plain-text message to a Telegram chat using the Bot API.

    Args:
        bot_token: Token of the Telegram bot.
        chat_id: Identifier of the target chat (user, group or channel).
        message: Text content to send.

    Returns:
        The JSON-decoded response returned by the Telegram API.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, json=payload)
    return response.json()


if __name__ == "__main__":
    # Example usage. Replace the token and chat id with environment variables
    # or configuration values before running this module directly.
    MESSAGE = "Hello, this is a test message from Python!"

    result = send_telegram_message(BOT_TOKEN, CHAT_ID, MESSAGE)
    print(result)
