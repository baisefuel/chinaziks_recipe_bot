from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from add_recipe import save_recipe, start_add_recipe
from search import RECIPES_PER_PAGE, search, translate_to_ru
import ast

COMMENTS_PER_PAGE = 1

async def show_comments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    recipe_id = int(query.data.split("_")[-1])
    context.user_data["comments_recipe_id"] = recipe_id
    context.user_data["comments_page"] = 0

    await comment_page(update, context)

async def comment_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    recipe_id = context.user_data.get("comments_recipe_id")
    page = context.user_data.get("comments_page", 0)
    selected_index = context.user_data.get("selected_index", 0)

    conn = context.bot_data["db_conn"]
    cursor = conn.cursor()
    cursor.execute("""
        SELECT comment, username, created_at
        FROM comments
        WHERE recipe_id = %s
        ORDER BY created_at ASC
    """, (recipe_id,))
    comments = cursor.fetchall()
    keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]

    if not comments:
        await update.callback_query.edit_message_text("Нет комментариев к этому рецепту.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    total = len(comments)
    page = max(0, min(page, total - 1))

    text, username, created_at = comments[page]
    formatted = (
        f'Комментарии к рецепту "{get_recipe_title(recipe_id, cursor, context.user_data.get("lang", "en"))}"\n\n'
        f'Комментарий:\n{text}\n\n'
        f'Пользователь: {username or "Аноним"}\n'
        f'Дата: {created_at.strftime("%d/%m/%Y")}'
    )

    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️", callback_data="comment_prev"))
    else:
        pagination_row.append(InlineKeyboardButton(" ", callback_data="noop"))

    if page < total - 1:
        pagination_row.append(InlineKeyboardButton("➡️", callback_data="comment_next"))
    else:
        pagination_row.append(InlineKeyboardButton(" ", callback_data="noop"))

    selected_index = context.user_data.get("selected_index", 0)

    keyboard = [
        pagination_row,
        [InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")],
        [InlineKeyboardButton("🏠 В меню", callback_data="back")]
    ]
    await update.callback_query.edit_message_text(text=formatted, reply_markup=InlineKeyboardMarkup(keyboard))

def get_recipe_title(recipe_id, cursor, user_lang="en"):
    cursor.execute("SELECT name FROM recipes WHERE id = %s", (recipe_id,))
    row = cursor.fetchone()
    if not row:
        return "Название недоступно"

    name = row[0]
    return translate_to_ru(name) if user_lang == "ru" else name

async def comment_pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    page = context.user_data.get("comments_page", 0)

    if data == "comment_prev":
        page -= 1
    elif data == "comment_next":
        page += 1

    context.user_data["comments_page"] = page
    await comment_page(update, context)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = context.user_data.get("lang", "en")

    def maybe_translate(text):
        return translate_to_ru(text) if lang == "ru" else text

    def format_steps(text):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                cleaned_steps = [step.strip().strip('"').strip("'") for step in parsed]
                return "\n".join([f"{i+1}. {step}" for i, step in enumerate(cleaned_steps)])
            return text
        except:
            return text
        
    def clean_list_text(text):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, list):
                return ", ".join(item.strip().strip('"').strip("'") for item in parsed)
            return text
        except:
            return text

    if data == 'back':
        keyboard = [
            [InlineKeyboardButton("Найти рецепт🔍", callback_data='search')],
            [InlineKeyboardButton("Добавить рецепт➕", callback_data='add_recipe')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Добро пожаловать в Treat's Searcher! 👨🏾‍🦯\n"
            "Бот для интеллектуального поиска лучших рецептов 🥵\n"
            "Что ты хочешь сделать? 😊",
            reply_markup=reply_markup
        )

    elif data == 'search':
        keyboard = [
            [InlineKeyboardButton("ru", callback_data='lang_ru')],
            [InlineKeyboardButton("en", callback_data='lang_en')],
            [InlineKeyboardButton("Назад ⏪", callback_data='back')]
        ]
        await query.edit_message_text("Выбери язык поиска:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data in ['lang_ru', 'lang_en']:
        context.user_data["lang"] = 'ru' if data == 'lang_ru' else 'en'
        keyboard = [
            [InlineKeyboardButton("Найти по названию блюда 🍽", callback_data='search_by_name')],
            [InlineKeyboardButton("Найти по ингредиенту 🍗", callback_data='search_by_ingredients')],
            [InlineKeyboardButton("Найти пользовательские рецепты", callback_data='search_user_recipes')],
            [InlineKeyboardButton("Назад ⏪", callback_data='back')]
        ]
        await query.edit_message_text("Как ты хочешь найти рецепт?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'search_by_name':
        context.user_data["mode"] = "name"
        await query.edit_message_text('✍️ Введите название блюда или его часть:\nНапример: "борщ", "пирожки", "салат"')

    elif data == 'search_by_ingredients':
        context.user_data["mode"] = "ingredients"
        await query.edit_message_text('✍️ Введите ингредиенты через запятую:\nНапример: "картофель, морковь, лук"')

    elif data == 'search_user_recipes':
        context.user_data["mode"] = "user_recipes"
        context.user_data["search_text"] = "Пользовательские рецепты"
        context.user_data["page"] = 1
        await search(update, context, is_callback=True)

    elif data == "enter_servings_filter":
        await query.edit_message_text("Введите желаемое количество порций:")
        context.user_data["awaiting_servings_input"] = True

    elif data == "remove_servings_filter":
        context.user_data.pop("servings_filter", None)
        context.user_data["page"] = 1
        await search(update, context, is_callback=True)

    elif data == 'next_page':
        context.user_data["page"] += 1
        await search(update, context, is_callback=True)

    elif data == 'prev_page':
        context.user_data["page"] -= 1
        await search(update, context, is_callback=True)

    elif data == 'back_to_mode':
        context.user_data.pop("search_text", None)
        context.user_data.pop("page", None)
        context.user_data.pop("selected_recipe_id", None)
        keyboard = [
            [InlineKeyboardButton("Найти по названию блюда 🍽", callback_data='search_by_name')],
            [InlineKeyboardButton("Найти по ингредиенту 🍗", callback_data='search_by_ingredients')],
            [InlineKeyboardButton("Найти пользовательские рецепты", callback_data='search_user_recipes')],
            [InlineKeyboardButton("Назад ⏪", callback_data='back')]
        ]
        await query.edit_message_text("Как ты хочешь найти рецепт?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == 'noop':
        return

    elif data.startswith("select_"):
        parts = data.split("_")
        if len(parts) != 2 or not parts[1].isdigit():
            return

        selected_index = int(parts[1]) - 1

        recipe_ids = context.user_data.get("full_search_results", [])
        if selected_index < 0 or selected_index >= len(recipe_ids):
            await query.edit_message_text("Что-то пошло не так. Начни заново /start")
            return

        recipe_id = recipe_ids[selected_index]
        context.user_data["selected_recipe_id"] = recipe_id
        context.user_data["selected_index"] = selected_index

        cursor = context.bot_data["db_conn"].cursor()
        cursor.execute("SELECT name FROM recipes WHERE id = %s", (recipe_id,))
        row = cursor.fetchone()
        recipe_name = maybe_translate(row[0]) if row else "Неизвестный рецепт"

        keyboard = [
            [InlineKeyboardButton("🥕 Ингредиенты", callback_data="recipe_ingredients")],
            [InlineKeyboardButton("🧾 Граммовки", callback_data="recipe_ingredients_raw")],
            [InlineKeyboardButton("📖 Шаги приготовления", callback_data="recipe_steps")],
            [InlineKeyboardButton("🍽 Порции", callback_data="recipe_servings")],
            [InlineKeyboardButton("📏 Размер порции", callback_data="recipe_serving_size")],
            [InlineKeyboardButton("ℹ️ Полная информация", callback_data="recipe_full")],
            [
                InlineKeyboardButton("Поставить/изменить ⭐️", callback_data=f"rate_recipe_{recipe_id}"),
                InlineKeyboardButton("Посмотреть среднюю ⭐️", callback_data=f"view_rating_{recipe_id}")
            ],
            [
                InlineKeyboardButton("Оставить 💬", callback_data=f"comment_{recipe_id}"),
                InlineKeyboardButton("Посмотреть 💬", callback_data=f"view_comments_{recipe_id}")
            ],
            [InlineKeyboardButton("🔙 Назад к результатам", callback_data="back_to_results")],
        ]

        await query.edit_message_text(
            f'Вы выбрали рецепт: "{recipe_name}"\nЧто вы хотите узнать?',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data.startswith("recipe_"):
        recipe_id = context.user_data.get("selected_recipe_id")
        selected_index = context.user_data.get("selected_index", 0)

        if not recipe_id:
            await query.edit_message_text("Сначала выбери рецепт.")
            return

        cursor = context.bot_data["db_conn"].cursor()

        if data == "recipe_ingredients":
            cursor.execute("SELECT ingredients FROM recipes WHERE id = %s", (recipe_id,))
            ingredients = cursor.fetchone()[0]
            cleaned = clean_list_text(ingredients)
            translated = maybe_translate(cleaned)
            keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]
            await query.edit_message_text(f"🥕 Ингредиенты:\n{translated}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "recipe_ingredients_raw":
            cursor.execute("SELECT ingredients_raw FROM recipes WHERE id = %s", (recipe_id,))
            raw = cursor.fetchone()[0]
            cleaned = clean_list_text(raw)
            translated = maybe_translate(cleaned)
            keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]
            await query.edit_message_text(f"🧾 Граммовки:\n{translated}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "recipe_steps":
            cursor.execute("SELECT steps FROM recipes WHERE id = %s", (recipe_id,))
            steps = cursor.fetchone()[0]
            cleaned = clean_list_text(steps)
            translated = maybe_translate(cleaned)
            formatted = format_steps(translated)
            keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]
            await query.edit_message_text(f"📖 Шаги приготовления:\n{formatted}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "recipe_servings":
            cursor.execute("SELECT servings FROM recipes WHERE id = %s", (recipe_id,))
            servings = cursor.fetchone()[0]
            keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]
            await query.edit_message_text(f"🍽 Порции: {servings}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "recipe_serving_size":
            cursor.execute("SELECT serving_size FROM recipes WHERE id = %s", (recipe_id,))
            size = cursor.fetchone()[0]
            keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]
            await query.edit_message_text(f"📏 Размер порции: {size}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "recipe_full":
            cursor.execute("""
                SELECT name, ingredients, ingredients_raw, steps, servings, serving_size, created_by 
                FROM recipes WHERE id = %s
            """, (recipe_id,))
            row = cursor.fetchone()
            if not row:
                await query.edit_message_text("Информация о рецепте недоступна.")
                return

            name, ingredients, raw, steps, servings, size, creator = row
            creator_info = creator if creator else "Создатель неизвестен (данные из датасета)"
            
            translated_name = maybe_translate(name)
            translated_ingredients = maybe_translate(clean_list_text(ingredients))
            translated_raw = maybe_translate(clean_list_text(raw))
            translated_steps = format_steps(maybe_translate(clean_list_text(steps)))

            full_info = (
                f"📛 Название: {translated_name}\n"
                f"🥕 Ингредиенты: {translated_ingredients}\n"
                f"🧾 Граммовки: {translated_raw}\n"
                f"📖 Шаги приготовления:\n{translated_steps}\n"
                f"🍽 Порции: {servings}\n"
                f"📏 Размер порции: {size}\n"
                f"👨‍🍳 {creator_info}"
            )
            keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]
            await query.edit_message_text(full_info, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "back_to_results":
        await search(update, context, is_callback=True)
    
    elif data == 'add_recipe':
        await start_add_recipe(update, context)
    
    elif data == "lang_ru_add":
        context.user_data["add_recipe"]["lang"] = "ru"
        await save_recipe(update, context)

    elif data == "lang_en_add":
        context.user_data["add_recipe"]["lang"] = "en"
        await save_recipe(update, context)

    elif data.startswith("view_comments_"):
        recipe_id = int(data.replace("view_comments_", ""))
        context.user_data["comments_recipe_id"] = recipe_id
        context.user_data["comments_page"] = 0
        await comment_page(update, context)
    
    elif data.startswith("rate_recipe_"):
        recipe_id = int(data.split("_")[-1])
        context.user_data["rating_recipe_id"] = recipe_id
        context.user_data["awaiting_rating"] = True
        await query.message.reply_text("Поставьте оценку от 1 до 5:")

    elif data.startswith("view_rating_"):
        selected_index = context.user_data.get("selected_index", 0)
        recipe_id = int(data.split("_")[-1])
        cursor = context.bot_data["db_conn"].cursor()
        cursor.execute("SELECT AVG(rating), COUNT(*) FROM ratings WHERE recipe_id = %s", (recipe_id,))
        avg, count = cursor.fetchone()
        keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]

        if count == 0:
            await query.edit_message_text("Оценок пока нет для этого рецепта.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text(f"Средняя оценка: ⭐ {round(avg, 2)} (на основе {count} оценок)", reply_markup=InlineKeyboardMarkup(keyboard))


async def comment_entry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("comment_"):
        return

    recipe_id = int(data.replace("comment_", ""))
    context.user_data["comment_recipe_id"] = recipe_id
    context.user_data["awaiting_comment"] = True

    await query.message.reply_text("Напиши комментарий к рецепту:")

async def handle_rating_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_rating"):
        return

    user_input = update.message.text.strip()
    if not user_input.isdigit() or not (1 <= int(user_input) <= 5):
        await update.message.reply_text("Пожалуйста, введите число от 1 до 5.")
        return

    rating = int(user_input)
    recipe_id = context.user_data.get("rating_recipe_id")
    user_id = update.message.from_user.id
    selected_index = context.user_data.get("selected_index", 0)

    conn = context.bot_data["db_conn"]
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO ratings (recipe_id, user_id, rating)
        VALUES (%s, %s, %s)
        ON CONFLICT (recipe_id, user_id)
        DO UPDATE SET rating = EXCLUDED.rating, created_at = CURRENT_TIMESTAMP
    """, (recipe_id, user_id, rating))
    conn.commit()

    context.user_data.pop("awaiting_rating", None)
    context.user_data.pop("rating_recipe_id", None)
    keyboard = [[InlineKeyboardButton("🔙 Назад к рецепту", callback_data=f"select_{selected_index + 1}")]]

    await update.message.reply_text("Спасибо за вашу оценку! ⭐", reply_markup=InlineKeyboardMarkup(keyboard))
