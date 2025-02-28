import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config.config import TELEGRAM_TOKEN
from core.chatbot import Chatbot
from utils.logger import log_info, log_error

chatbot = Chatbot()

async def start(update, context):
    user_id = str(update.message.from_user.id)
    log_info(f"User {user_id} started the bot")
    await update.message.reply_text(
        "Welcome to the Cybercrime Bot! Report any cybercrime by sending a message. "
        "Supported languages: English, Hindi, Telugu. Use /lang <en/hi/te> to switch languages. "
        "Use /trends to see recent threat trends."
    )

async def set_language(update, context):
    user_id = str(update.message.from_user.id)
    try:
        lang = context.args[0].lower()
        chatbot.set_language(lang)
        await update.message.reply_text(f"Language set to {lang}")
    except IndexError:
        log_error(f"User {user_id} provided no language argument")
        await update.message.reply_text("Please specify a language: /lang <en/hi/te>")

async def show_trends(update, context):
    user_id = str(update.message.from_user.id)
    response = chatbot.process_input("trends", user_id)
    await update.message.reply_text(response)

async def handle_message(update, context):
    user_id = str(update.message.from_user.id)
    user_input = update.message.text
    log_info(f"Received message from {user_id}: {user_input}")
    
    response = chatbot.process_input(user_input, user_id)
    await update.message.reply_text(response)

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lang", set_language))
    application.add_handler(CommandHandler("trends", show_trends))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log_info("Telegram bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()