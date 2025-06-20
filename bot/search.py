import os
from dotenv import load_dotenv
from translatepy import Translator
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
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

    if context.user_data.get("awaiting_comment"):
        recipe_id = context.user_data.get("comment_recipe_id")
        comment_text = update.message.text.strip()
        user = update.effective_user
        selected_index = context.user_data.get("selected_index", 0)

        if not comment_text:
            await update.message.reply_text("Комментарий не может быть пустым.")
            return

        db_conn = context.bot_data["db_conn"]
        cursor = db_conn.cursor()
        cursor.execute("""
            INSERT INTO comments (recipe_id, user_id, username, comment)
            VALUES (%s, %s, %s, %s)
        """, (
            recipe_id,
            user.id,
            f"@{user.username}" if user.username else "Аноним",
            comment_text
        ))
        db_conn.commit()
        cursor.close()

        context.user_data.pop("awaiting_comment")
        context.user_data.pop("comment_recipe_id")
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")],
            [InlineKeyboardButton("⏪ Назад в меню", callback_data='back')]
        ]

        await update.message.reply_text("Комментарий успешно добавлен ✅", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    elif mode in ["name", "ingredients"]:
        context.user_data["search_text"] = user_text
        context.user_data["page"] = 1
        await search(update, context)
    else:
        await update.message.reply_text("Сначала выбери режим поиска через кнопки!")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    user_data = context.user_data
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    db_conn = context.bot_data["db_conn"]
    context.user_data.pop("full_search_results", None)

    language = user_data.get("lang")
    mode = user_data.get("mode")
    search_text = user_data.get("search_text", "Пользовательские рецепты")
    page = user_data.get("page", 1)
    servings_filter = user_data.get("servings_filter")
    query = update.callback_query if is_callback else None

    if not mode or not language:
        img_path = os.path.join(BASE_DIR, "..", "resources", "images", "error.jpg")
        keyboard = [[InlineKeyboardButton("⏪ Назад", callback_data="back_to_mode")]]
        
        if is_callback:
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=open(img_path, 'rb'),
                    caption="Что-то пошло не так, начни сначала!"
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_photo(
                photo=open(img_path, 'rb'),
                caption="Что-то пошло не так, начни сначала!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    query_en = translate_to_en(search_text) if mode != "user_recipes" else ""
    query_ru = search_text if mode != "user_recipes" else "Пользовательские рецепты"
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
        img_path = os.path.join(BASE_DIR, "..", "resources", "images", "search_recipes.png")
        
        if is_callback:
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=open(img_path, 'rb'),
                    caption=f'К сожалению, рецепты по запросу "{search_text}" не найдены.'
                ),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_photo(
                photo=open(img_path, 'rb'),
                caption=f'К сожалению, рецепты по запросу "{search_text}" не найдены.',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    recipe_ids = [row[0] for row in results]
    if "full_search_results" not in context.user_data:
        full_cursor = db_conn.cursor()

        if mode == 'name':
            full_sql = """
                SELECT id FROM recipes
                WHERE (LOWER(name) LIKE %s OR LOWER(name) LIKE %s OR LOWER(name) = LOWER(%s) OR LOWER(name) = LOWER(%s))
            """
            full_params = [f"%{query_ru.lower()}%", f"%{query_en.lower()}%", f"%{query_ru.lower()}%", f"%{query_en.lower()}%"]
            if servings_filter:
                full_sql += " AND servings = %s"
                full_params.append(servings_filter)

            full_sql += " ORDER BY id"
            full_cursor.execute(full_sql, full_params)

        elif mode == 'ingredients':
            full_sql = f"""
                SELECT id FROM recipes
                WHERE {" AND ".join(conditions)}
            """
            if servings_filter:
                full_sql += " AND servings = %s"
                params.append(servings_filter)

            full_sql += " ORDER BY id"
            full_cursor.execute(full_sql, params[:len(params)-2])

        elif mode == "user_recipes":
            full_sql = """
                SELECT id FROM recipes
                WHERE created_by IS NOT NULL
            """
            full_params = []
            if servings_filter:
                full_sql += " AND servings = %s"
                full_params.append(servings_filter)

            full_sql += " ORDER BY id DESC"
            full_cursor.execute(full_sql, full_params)

        full_results = full_cursor.fetchall()
        full_recipe_ids = [row[0] for row in full_results]
        context.user_data["full_search_results"] = full_recipe_ids

    all_recipe_ids = context.user_data["full_search_results"]
    start = (page - 1) * RECIPES_PER_PAGE
    end = start + RECIPES_PER_PAGE
    current_page_ids = all_recipe_ids[start:end]
    context.user_data["search_results"] = current_page_ids

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
        img_path = os.path.join(BASE_DIR, '..', 'resources', 'images', 'search_recipes.png')

        if is_callback:
            with open(img_path, 'rb') as img:
                await query.edit_message_media(
                    media=InputMediaPhoto(
                        media=img,
                        caption=message_text
                    ),
                    reply_markup=reply_markup
                )
        else:
            with open(img_path, 'rb') as img:
                await update.message.reply_photo(
                    photo=img,
                    caption=message_text,
                    reply_markup=reply_markup
                )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise