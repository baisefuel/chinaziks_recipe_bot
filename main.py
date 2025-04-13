import os
from dotenv import load_dotenv
import telegram

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
CHAT_ID = os.getenv('TG_CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_TOKEN)