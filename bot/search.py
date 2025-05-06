import os
from dotenv import load_dotenv
from translatepy import Translator
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from add_recipe import handle_add_recipe

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
    if "add_recipe" in context.user_data:
        await handle_add_recipe(update, context)
        return

    if context.user_data.get("awaiting_servings_input"):
        servings_input = update.message.text.strip()
        if servings_input.isdigit() and int(servings_input) > 0:
            context.user_data["servings_filter"] = int(servings_input)
            context.user_data.pop("awaiting_servings_input")
            context.user_data["page"] = 1
            await search(update, context)
        else:
            await update.message.reply_text("Пожалуйста, введите корректное число (целое и больше нуля).")
        return

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
    
    servings_filter = user_data.get("servings_filter")

    if not search_text or not mode or not language:
        keyboard = [[InlineKeyboardButton("⏪ Назад", callback_data="back_to_mode")]]
        await update.message.reply_text("Что-то пошло не так, начни сначала!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    query_en = translate_to_en(search_text)
    query_ru = search_text
    current_page = (page - 1) * RECIPES_PER_PAGE

    cursor = db_conn.cursor()
    
    if mode == 'name':
        sql = """
            SELECT id, name FROM recipes
            WHERE (LOWER(name) LIKE %s OR LOWER(name) LIKE %s OR LOWER(name) = LOWER(%s) OR LOWER(name) = LOWER(%s))
        """
        params = [f"%{query_ru.lower()}%", f"%{query_en.lower()}%", f"%{query_ru.lower()}%", f"%{query_en.lower()}%"]

        if servings_filter:
            sql += " AND servings = %s"
            params.append(servings_filter)

        sql += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([RECIPES_PER_PAGE, current_page])
        cursor.execute(sql, params)

    elif mode == 'ingredients':
        ingredients_en = [word.strip().lower() for word in query_en.split(',')]
        ingredients_ru = [word.strip().lower() for word in query_ru.split(',')]

        conditions = []
        params = []
        for ing_ru, ing_en in zip(ingredients_ru, ingredients_en):
            conditions.append("(LOWER(ingredients) LIKE %s OR LOWER(ingredients) LIKE %s)")
            params.append(f"%{ing_ru}%")
            params.append(f"%{ing_en}%")

        sql = f"""
            SELECT id, name FROM recipes
            WHERE {" AND ".join(conditions)}
        """
        if servings_filter:
            sql += " AND servings = %s"
            params.append(servings_filter)

        sql += " ORDER BY id LIMIT %s OFFSET %s"
        params.extend([RECIPES_PER_PAGE, current_page])
        cursor.execute(sql, params)

    elif mode == "user_recipes":
        sql = """
            SELECT id, name FROM recipes
            WHERE created_by IS NOT NULL
        """
        params = []

        if servings_filter:
            sql += " AND servings = %s"
            params.append(servings_filter)

        sql += " ORDER BY id DESC LIMIT %s OFFSET %s"
        params.extend([RECIPES_PER_PAGE, current_page])
        cursor.execute(sql, params)

    results = cursor.fetchall()

    if not results:
        keyboard = [[InlineKeyboardButton("⏪ Назад", callback_data="back_to_mode")]]
        await update.message.reply_text(
            f'К сожалению, рецепты по запросу "{search_text}" не найдены.\nПроверьте правильность написания вашего запроса или попробуйте другой вариант поиска.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    recipe_ids = [row[0] for row in results]
    context.user_data["search_results"] = recipe_ids

    message_lines = []
    for i, row in enumerate(results):
        recipe_name = row[1]
        if language == "ru":
            recipe_name = translate_to_ru(recipe_name)
        message_lines.append(f"{i + 1 + current_page}. {recipe_name}")

    message_text = f'Вот рецепты по запросу "{search_text}":\n' + "\n".join(message_lines)

    pagination_row = []
    if page > 1:
        pagination_row.append(InlineKeyboardButton("⬅️", callback_data="prev_page"))
    else:
        pagination_row.append(InlineKeyboardButton(" ", callback_data="noop"))

    for i, row in enumerate(results):
        index = str(i + 1 + current_page)
        pagination_row.append(InlineKeyboardButton(index, callback_data=f"select_{index}"))

    if len(results) == RECIPES_PER_PAGE:
        pagination_row.append(InlineKeyboardButton("➡️", callback_data="next_page"))
    else:
        pagination_row.append(InlineKeyboardButton(" ", callback_data="noop"))

    if context.user_data.get("servings_filter"):
        filter_button = InlineKeyboardButton("Убрать фильтр по порциям", callback_data="remove_servings_filter")
    else:
        filter_button = InlineKeyboardButton("Ввести количество порций", callback_data="enter_servings_filter")

    keyboard = [
        pagination_row,
        [filter_button],
        [InlineKeyboardButton("⏪ Назад", callback_data="back_to_mode")],
        [InlineKeyboardButton("🔙 Меню", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if is_callback:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise
