from telegram import Update
from telegram.ext import ContextTypes

async def start_add_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_recipe"] = {}

    if update.message:
        await update.message.reply_text("✍️ Введите название блюда:")
    elif update.callback_query:
        await update.callback_query.message.reply_text("✍️ Введите название блюда:")

async def handle_add_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "add_recipe" not in context.user_data:
        await update.message.reply_text("Чтобы добавить рецепт, сначала нажмите кнопку 'Добавить рецепт'. Введи /start заново.")
        return

    recipe_data = context.user_data["add_recipe"]
    text = update.message.text

    if "name" not in recipe_data:
        recipe_data["name"] = text
        await update.message.reply_text("🥕 Теперь введите ингредиенты через запятую:")
    elif "ingredients" not in recipe_data:
        recipe_data["ingredients"] = text
        await update.message.reply_text("📋 Теперь введите грамовки через запятую (или напишите 'нет'):")
    elif "ingredients_raw" not in recipe_data:
        recipe_data["ingredients_raw"] = text if text.lower() != "нет" else ""
        await update.message.reply_text("📖 Теперь напишите пошаговую инструкцию (каждый шаг с новой строки):")
    elif "steps" not in recipe_data:
        recipe_data["steps"] = text
        await update.message.reply_text("🍽 Сколько порций получается?")
    elif "servings" not in recipe_data:
        recipe_data["servings"] = text
        await update.message.reply_text("⚖️ Какой размер одной порции?")
    elif "serving_size" not in recipe_data:
        recipe_data["serving_size"] = text
        await save_recipe(update, context)

async def save_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_conn = context.bot_data["db_conn"]
    recipe_data = context.user_data["add_recipe"]
    lang = context.user_data.get("lang", "en")

    name = recipe_data["name"]
    ingredients = recipe_data["ingredients"]
    ingredients_raw = recipe_data["ingredients_raw"]
    steps = recipe_data["steps"]
    servings = recipe_data["servings"]
    serving_size = recipe_data["serving_size"]
    created_by = update.effective_user.first_name or "Пользователь"

    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO recipes (name, ingredients, ingredients_raw, steps, servings, serving_size, created_by, lang)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        name, ingredients, ingredients_raw, steps, servings, serving_size, created_by,
        "ru" if lang == "ru" else None
    ))
    db_conn.commit()

    await update.message.reply_text("✅ Рецепт успешно добавлен! Спасибо!")

    context.user_data.pop("add_recipe", None)