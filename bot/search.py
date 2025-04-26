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
    if "add_recipe" in context.user_data:
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

    if not search_text or not mode or not language:
        keyboard = [[InlineKeyboardButton("⏪ Назад", callback_data="back_to_mode")]]
        await update.message.reply_text("Что-то пошло не так, начни сначала!", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    query = translate_to_en(search_text) if language == "ru" else search_text
    current_page = (page - 1) * RECIPES_PER_PAGE

    cursor = db_conn.cursor()
    if mode == 'name':
        cursor.execute(
            "SELECT id, name FROM recipes WHERE LOWER(name) LIKE %s ORDER BY id LIMIT %s OFFSET %s",
            (f"%{query.lower()}%", RECIPES_PER_PAGE, current_page)
        )
    elif mode == 'ingredients':
        ingredients = [word.strip().lower() for word in query.split(',')]
        sql = "SELECT id, name FROM recipes WHERE " + " AND ".join(
            ["LOWER(ingredients_raw) LIKE %s" for _ in ingredients]
        ) + " ORDER BY id LIMIT %s OFFSET %s"
        params = [f"%{ingredient}%" for ingredient in ingredients] + [RECIPES_PER_PAGE, current_page]
        cursor.execute(sql, params)

    results = cursor.fetchall()

    if not results:
        keyboard = [[InlineKeyboardButton("⏪ Назад", callback_data="back_to_mode")]]
        await update.message.reply_text(
            f'К сожалению, рецепты по запросу "{search_text}" не найдены.',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    recipe_ids = [row[0] for row in results]
    context.user_data["search_results"] = recipe_ids

    message_lines = []
    for i, row in enumerate(results):
        name = translate_to_ru(row[1]) if language == "ru" else row[1]
        message_lines.append(f"{i + 1 + current_page}. {name}")

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

    keyboard = [
        pagination_row,
        [InlineKeyboardButton("⏪ Назад", callback_data="back_to_mode")],
        [InlineKeyboardButton("🔙 Меню", callback_data="back")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_callback:
        await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

async def show_recipe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, recipe_id: int):
    db_conn = context.bot_data["db_conn"]
    language = context.user_data.get("lang")

    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM recipes WHERE id = %s", (recipe_id,))
    row = cursor.fetchone()

    if not row:
        await update.callback_query.edit_message_text("Рецепт не найден.")
        return

    name = translate_to_ru(row[0]) if language == "ru" else row[0]
    context.user_data["selected_recipe_id"] = recipe_id

    text = f'Вы выбрали рецепт: "{name}"\nЧто вы хотите узнать?'
    keyboard = [
        [InlineKeyboardButton("📝 Ингредиенты", callback_data="recipe_ingredients")],
        [InlineKeyboardButton("📋 Грамовки", callback_data="recipe_ingredients_raw")],
        [InlineKeyboardButton("📖 Шаги", callback_data="recipe_steps")],
        [InlineKeyboardButton("🍽 Количество порций", callback_data="recipe_servings")],
        [InlineKeyboardButton("⚖️ Размер порции", callback_data="recipe_serving_size")],
        [InlineKeyboardButton("ℹ️ Подробная информация", callback_data="recipe_full")],
        [InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_results")]
    ]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_recipe_field(update: Update, context: ContextTypes.DEFAULT_TYPE, field: str):
    db_conn = context.bot_data["db_conn"]
    recipe_id = context.user_data.get("selected_recipe_id")
    language = context.user_data.get("lang")

    cursor = db_conn.cursor()
    cursor.execute(f"SELECT {field} FROM recipes WHERE id = %s", (recipe_id,))
    row = cursor.fetchone()

    if not row or not row[0]:
        text = "Информация отсутствует."
    else:
        value = row[0]
        if language == "ru":
            value = translate_to_ru(value)

        if field == "steps":
            lines = value.split('\n')
            value = "\n".join(f"{i+1}. {line.strip()}" for i, line in enumerate(lines) if line.strip())
        elif field in ["ingredients", "ingredients_raw"]:
            value = ", ".join([item.strip() for item in value.split(',') if item.strip()])

        text = f"{field.replace('_', ' ').capitalize()}:\n{value}"

    keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data="back_to_recipe")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_recipe_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_conn = context.bot_data["db_conn"]
    recipe_id = context.user_data.get("selected_recipe_id")
    language = context.user_data.get("lang")

    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT name, ingredients, steps, servings, serving_size, created_by FROM recipes WHERE id = %s",
        (recipe_id,)
    )
    row = cursor.fetchone()

    if not row:
        await update.callback_query.edit_message_text("Рецепт не найден.")
        return

    name, ingredients, steps, servings, serving_size, created_by = row

    if language == "ru":
        name = translate_to_ru(name)
        ingredients = translate_to_ru(ingredients)
        steps = translate_to_ru(steps)
        created_by = translate_to_ru(created_by)

    steps_list = "\n".join(f"{i+1}. {s.strip()}" for i, s in enumerate((steps or "").split('\n')) if s.strip())
    ingredients_list = ", ".join([i.strip() for i in (ingredients or "").split(',') if i.strip()])

    creator = created_by if created_by else "Источник неизвестен 🤷‍♂️ (Взято из датасета)"

    name = translate_to_ru(row[0]) if language == "ru" else row[0]
    text = f"""📌 <b>{name}</b>
    📝 <b>Ингредиенты:</b> {ingredients_list}
    📖 <b>Шаги:</b>\n{steps_list}
    🍽 <b>Количество порций:</b> {servings or "?"}
    ⚖️ <b>Размер порции:</b> {serving_size or "?"}
    👨‍🍳 <b>Создатель:</b> {creator}
    """
    keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data="back_to_recipe")]]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
