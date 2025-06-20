from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
import os

async def start_add_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_recipe"] = {}
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(BASE_DIR, '..', 'resources', 'images', 'add_recipe.png')

    caption = "✍️ Начнем с названия блюда. Например: «Овощное рагу» или «Chicken soup»"
    
    with open(img_path, 'rb') as photo:
        if update.message:
            await update.message.reply_photo(
                photo=photo,
                caption=caption
            )
        elif update.callback_query:
            await update.callback_query.message.reply_photo(
                photo=photo,
                caption=caption
            )

async def handle_add_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "add_recipe" not in context.user_data:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(BASE_DIR, '..', 'resources', 'images', 'add_recipe.png')
        
        with open(img_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="Чтобы добавить рецепт, сначала нажмите кнопку 'Добавить рецепт'. Введи /start заново."
            )
        return

    recipe_data = context.user_data["add_recipe"]
    text = update.message.text
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(BASE_DIR, '..', 'resources', 'images', 'add_recipe.png')

    if "name" not in recipe_data:
        recipe_data["name"] = text
        with open(img_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="📋 Отлично! Теперь введите список ингредиентов через запятую. Например: «картошка, морковь, лук» или «potatoes, carrots, onions»."
            )
    elif "ingredients" not in recipe_data:
        recipe_data["ingredients"] = text
        with open(img_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="⚖️ Спасибо! Теперь укажите количество каждого ингредиента с нужными единицами измерения через запятую. Например: «картошка 500 г, соль 1 щепотка, подсолнечное масло 2 ст. л.»."
            )
    elif "ingredients_raw" not in recipe_data:
        recipe_data["ingredients_raw"] = text if text.lower() != "нет" else ""
        with open(img_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption='👨‍🍳 Далее опишите пошагово, как приготовить это блюдо. Вы можете писать короткими предложениями или пунктами.\n'
                        'Например:\n'
                        '«1. Очистить и нарезать все овощи.\n'
                        '2. Варить говядину 1,5 часа на небольшом огне.\n'
                        '3. Добавить овощи и варить еще 10 минут.»'
            )
    elif "steps" not in recipe_data:
        recipe_data["steps"] = text
        with open(img_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="🍽 Укажите, сколько порций получается из этого рецепта? Введите целое натуральное число, например: «4»."
            )
    elif "servings" not in recipe_data:
        recipe_data["servings"] = text
        with open(img_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption='🍽 Укажите размер одной порции, например, в граммах: "250 г".'
            )
    elif "serving_size" not in recipe_data:
        recipe_data["serving_size"] = text

        keyboard = [
            [InlineKeyboardButton("ru", callback_data="lang_ru_add")],
            [InlineKeyboardButton("en", callback_data="lang_en_add")]
        ]
        
        with open(img_path, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption="🌎 Выберите язык рецепта:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

async def save_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_conn = context.bot_data["db_conn"]
    recipe_data = context.user_data["add_recipe"]
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(BASE_DIR, '..', 'resources', 'images', 'add_recipe.png')

    name = recipe_data["name"]
    ingredients = recipe_data["ingredients"]
    ingredients_raw = recipe_data["ingredients_raw"]
    steps = recipe_data["steps"]
    servings = recipe_data["servings"]
    serving_size = recipe_data["serving_size"]
    lang = recipe_data.get("lang", "en")

    created_by = update.effective_user.username or "Пользователь"
    if created_by:
        created_by = f"@{created_by}"
    else:
        created_by = None

    cursor = db_conn.cursor()
    cursor.execute("""
        INSERT INTO recipes (name, ingredients, ingredients_raw, steps, servings, serving_size, created_by, lang)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        name, ingredients, ingredients_raw, steps, servings, serving_size, created_by, lang
    ))
    db_conn.commit()

    keyboard = [
        [InlineKeyboardButton("Назад ⏪", callback_data='back')]
    ]

    with open(img_path, 'rb') as photo:
        if update.message:
            await update.message.reply_photo(
                photo=photo,
                caption="✅ Рецепт успешно добавлен! Спасибо!",
                reply_markup=InlineKeyboardMarkup(keyboard))
        elif update.callback_query:
            await update.callback_query.message.reply_photo(
                photo=photo,
                caption="✅ Рецепт успешно добавлен! Спасибо!",
                reply_markup=InlineKeyboardMarkup(keyboard))

    context.user_data.pop("add_recipe", None)