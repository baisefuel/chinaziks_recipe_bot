import os
from dotenv import load_dotenv
from telegram.ext import Application, CallbackQueryHandler, CommandHandler
from start import start
from callbacks import button_callback


dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv()
TOKEN = os.getenv("TG_TOKEN")

app = Application.builder().token(TOKEN).build()
    
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_callback))

app.run_polling()