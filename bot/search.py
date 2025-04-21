import os
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


#asyncio.run(TranslateText())

async def translate_to_en(text: str):
    return GoogleTranslator(source='ru', target='en').translate(text)

async def translate_to_ru(text: str):
    return GoogleTranslator(source='en', target='ru').translate(text)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    mode = context.user_data.get("mode")
    
    if mode in ["name", "ingredients"]:
        context.user_data["search_text"] = user_text
        context.user_data["page"] = 1 

        await search(update, context)
    else:
        await update.message.reply_text("Сначала выбери режим поиска через кнопки!")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    db_conn = context.bot_data["db_conn"]

    language = user_data.get("lang")
    mode = user_data.get("mode")
    search_text = user_data.get("search_text")
    print(type(search_text))
    print(language)
    if language == "ru":
        translated = await translate_to_en(search_text)
    else:
        translated = search_text

    print(translated)

    cursor = db_conn.cursor()
    if mode == 'name':
        cursor.execute("SELECT id, name FROM recipes WHERE LOWER(name) LIKE %s LIMIT 5", (f"%{translated.lower()}%",))
    elif mode == 'ingredients':
        ingredients = [word.strip().lower() for word in translated.split(',')]
        sql = "SELECT id, name FROM recipes WHERE " + " AND ".join(
            ["LOWER(ingredients_raw) LIKE %s" for _ in ingredients]
        )
        params = [f"%{ingredient}%" for ingredient in ingredients]
        cursor.execute(sql, params)
    results = cursor.fetchall()

    if not results:
        await update.message.reply_text("Ничего не найдено.")
        return

    message_parts = []
    for i, row in enumerate(results):
        if language == "ru":
            translated_name = await translate_to_ru(row[1])
        else:
            translated_name = row[1]
        message_parts.append(f"{i+1}. {translated_name}")
    message_text = "\n".join(message_parts)
    print(message_text)
    keyboard = [
        [InlineKeyboardButton(str(i+1), callback_data=f"select_{row[0]}") for i, row in enumerate(results)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(text=message_text, reply_markup=reply_markup)