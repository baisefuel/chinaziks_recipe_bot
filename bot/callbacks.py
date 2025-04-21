from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'back':
        keyboard = [
            [InlineKeyboardButton("Найти рецепт🔍", callback_data='search')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Добро пожаловать в Treat's Searcher! 👨🏾‍🦯\n"
        "Бот для интеллектуального поиска лучших рецептов 🥵\n"
        "Что ты хочешь сделать? 😊", reply_markup=reply_markup)


    if query.data == 'search':
        keyboard = [
            [InlineKeyboardButton("ru", callback_data='lang_ru')],
            [InlineKeyboardButton("en", callback_data='lang_en')],
            [InlineKeyboardButton("Назад ⏪", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Выбери язык поиска:", reply_markup=reply_markup)

    if query.data == "lang_en":
        context.user_data["lang"] = "en"
    elif query.data == "lang_ru":
        context.user_data["lang"] = "ru"

    if query.data in ['lang_ru', 'lang_en']:
        keyboard = [
            [InlineKeyboardButton("Найти по названию блюда 🍽", callback_data='search_by_name')],
            [InlineKeyboardButton("Найти по ингредиенту 🍗", callback_data='search_by_ingredients')],
            [InlineKeyboardButton("Назад ⏪", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Как ты хочешь найти рецепт?", reply_markup=reply_markup)

    if query.data == 'search_by_name':
        context.user_data["mode"] = "name"
        await query.edit_message_text("Введи название блюда для поиска:")

    if query.data == 'search_by_ingredients':
        context.user_data["mode"] = "ingredients"
        await query.edit_message_text("Введи ингредиенты через запятую для поиска:")