import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(BASE_DIR, '..', 'resources', 'images', 'hello.png')

    keyboard = [
        [InlineKeyboardButton("Найти рецепт🔍", callback_data='search')],
        [InlineKeyboardButton("Добавить рецепт➕", callback_data='add_recipe')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=open(img_path, 'rb'),
        caption="Добро пожаловать в Treat's Searcher! 👨🏾‍🦯\n"
        "Бот для интеллектуального поиска лучших рецептов 🥵\n"
        "Что ты хочешь сделать? 😊",
        reply_markup=reply_markup
    )
