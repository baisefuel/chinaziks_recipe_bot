import os

import telegram


TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_TOKEN)