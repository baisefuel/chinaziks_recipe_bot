import os
from dotenv import load_dotenv
from translatepy import Translator
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

translator = Translator()

def translate_to_en(text: str) -> str:
    return translator.translate(text, "English").result

def translate_to_ru(text: str) -> str:
    return translator.translate(text, "Russian").result

RECIPES_PER_PAGE = 5

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    mode = context.user_data.get("mode")
    
    if mode in ["name", "ingredients"]:
        context.user_data["search_text"] = user_text
        context.user_data["page"] = 1
        await search(update, context)
    else:
        await update.message.reply_text("Сначала выбери режим поиска через кнопки!")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_data = context.user_data
    db_conn = context.bot_data["db_conn"]

    language = user_data.get("lang")
    mode = user_data.get("mode")
    search_text = user_data.get("search_text")
    page = user_data.get("page", 1)

    if not search_text or not mode or not language:
        await update.message.reply_text("Что-то пошло не так, начни сначала через /start.")
        return

    if language == "ru":
        translated = translate_to_en(search_text)
    else:
        translated = search_text

    current_page = (page - 1) * RECIPES_PER_PAGE

    cursor = db_conn.cursor()
    if mode == 'name':
        cursor.execute(
            "SELECT id, name FROM recipes WHERE LOWER(name) LIKE %s ORDER BY id LIMIT %s OFFSET %s",
            (f"%{translated.lower()}%", RECIPES_PER_PAGE, current_page)
        )
    elif mode == 'ingredients':
        ingredients = [word.strip().lower() for word in translated.split(',')]
        sql = "SELECT id, name FROM recipes WHERE " + " AND ".join(
            ["LOWER(ingredients_raw) LIKE %s" for _ in ingredients]
        ) + " ORDER BY id LIMIT %s OFFSET %s"
        params = [f"%{ingredient}%" for ingredient in ingredients] + [RECIPES_PER_PAGE, current_page]
        cursor.execute(sql, params)

    results = cursor.fetchall()

    if not results:
        await update.message.reply_text(f'К сожалению, рецепты с запросом "{search_text}" не найдены. Проверьте правильность написания вашего запроса или воспользуйтесь поиском по ингредиентам.')
        return

    message_parts = []
    for i, row in enumerate(results):
        name = translate_to_ru(row[1]) if language == "ru" else row[1]
        message_parts.append(f"{i+1 + current_page}. {name}")
    message_text =f'Отлично! Вот рецепты, которые я нашел по запросу "{search_text}":\n'
    message_text += "\n".join(message_parts)

    recipe_buttons = [
        InlineKeyboardButton(str(i+1 + current_page), callback_data=f"select_{row[0]}")
        for i, row in enumerate(results)
    ]

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Предыдущая страница", callback_data="prev_page"))
    if len(results) == RECIPES_PER_PAGE:
        nav_buttons.append(InlineKeyboardButton("➡️ Следующая страница", callback_data="next_page"))

    keyboard = [
        recipe_buttons,
    ]
    if nav_buttons:
        keyboard.append(nav_buttons)
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_mode")])
    keyboard.append([InlineKeyboardButton("Вернуться в меню", callback_data="back")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_callback:
        await update.callback_query.edit_message_text(text=message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text=message_text, reply_markup=reply_markup)