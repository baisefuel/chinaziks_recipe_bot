import os
from dotenv import load_dotenv
import psycopg2
from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from search import handle_text
from start import start
from callbacks import button_callback
from telegram.ext import MessageHandler, filters


dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv()

TOKEN = os.getenv("TG_TOKEN")

connection = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user = os.getenv("DB_USER"),
    host = os.getenv("DB_HOST"),
    password = os.getenv("DB_PASSWORD")
)

cursor = connection.cursor()

app = Application.builder().token(TOKEN).build()

app.bot_data["db_conn"] = connection

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()

