import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("TG_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Найти рецепт🔍", callback_data='search')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Добро пожаловать в Treat's Searcher! 👨🏾‍🦯\n"
        "Бот для интеллектуального поиска лучших рецептов 🥵\n"
        "Что ты хочешь сделать? 😊",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Найти по названию блюда 🍽", callback_data='search_by_name')],
        [InlineKeyboardButton("Найти по ингредиенту 🍗", callback_data='search_by_igredients')],
        [InlineKeyboardButton("Назад ⏪", callback_data='back')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query.data == 'search':
        await query.edit_message_text(text="Как ты хочешь найти рецепт?", reply_markup=reply_markup)
    elif query.data == 'back':
        keyboard = [
            [InlineKeyboardButton("Найти рецепт🔍", callback_data='search')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Добро пожаловать в Treat's Searcher! 👨🏾‍🦯\n"
        "Бот для интеллектуального поиска лучших рецептов 🥵\n"
        "Что ты хочешь сделать? 😊", reply_markup=reply_markup)


def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()

if __name__ == "__main__":
    main()
