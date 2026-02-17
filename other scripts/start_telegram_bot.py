import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


class TelegramMessenger:
    """
    Minimal Telegram bot used to discover chat and user IDs.

    When running, the bot echoes back the chat id and user id for any
    incoming text message so that they can be reused in other scripts.
    """

    def __init__(self, bot_token, log_level=logging.INFO):
        self.bot_token = bot_token
        self.logger = self._setup_logger(log_level)
        self.application = ApplicationBuilder().token(self.bot_token).build()

    def _setup_logger(self, log_level):
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    async def echo_chat_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        message = f"Chat ID: {chat_id}\nUser ID: {user_id}"
        await update.message.reply_text(message)
        self.logger.info(f"Echoed chat ID {chat_id} to user {user_id}")

    def start_bot(self):
        self.application.add_handler(CommandHandler("start", self.echo_chat_id))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.echo_chat_id))
        self.logger.info("Bot started. Use Ctrl-C to stop.")
        self.application.run_polling()

if __name__ == "__main__":
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    messenger = TelegramMessenger(BOT_TOKEN)
    messenger.start_bot()
