from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    
    keyboard = [
        [InlineKeyboardButton("Найти рецепт🔍", callback_data='search')],
        [InlineKeyboardButton("Добавить рецепт➕", callback_data='add_recipe')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Добро пожаловать в Treat's Searcher! 👨🏾‍🦯\n"
        "Бот для интеллектуального поиска лучших рецептов 🥵\n"
        "Что ты хочешь сделать? 😊",
        reply_markup=reply_markup
    )
