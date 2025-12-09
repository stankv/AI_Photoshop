from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackQueryHandler, CommandHandler
import os
from ai import *
from util import *


async def start(update, context):
    session.mode = 'main'
    text = load_message(session.mode)
    await send_photo(update, context, session.mode)
    await send_text(update, context, text)

    user_id = update.message.from_user.id
    create_user_dir(user_id)

    await show_main_menu(update, context, {
        "start": "🧟‍♂️ Главное меню бота",
        "image": "⚰️ Создаем картинку",
        "edit": "🧙‍♂️ Изменяем картинку",
        "merge": "📸 Объединяем картинки",
        "party": "🎃 Фото для Halloween - вечеринки",
        "video": "🎬☠️ страшное Halloween-видео из фото ",
    })


async def create_command(update, context):
    session.mode = 'create'
    text = load_message(session.mode)
    await send_photo(update, context, session.mode)
    await send_text_buttons(update, context, text, {
        "create_anime": "👧️ Аниме",
        "create_photo": "📸 Фото",
    }, checkbox_key=session.image_type)


async def create_button(update, context):
    await update.callback_query.answer()
    query = update.callback_query.data
    session.image_type = query
    text = load_message(session.mode)
    message = update.callback_query.message
    await edit_text_buttons(message, text, {
        "create_anime": "👧️ Аниме",
        "create_photo": "📸 Фото",
    }, checkbox_key=session.image_type)


async def create_message(update, context):
    text = update.message.text
    user_id = update.message.from_user.id

    photo_path = f'resources/users/{user_id}/photo.jpg'
    prompt = load_prompt(session.image_type)

    ai_create_image(prompt=prompt + text, output_path=photo_path)
    await send_photo(update, context, photo_path)


async def on_message(update, context):
    if session.mode == 'create':
        await create_message(update, context)
    else:
        await send_text(update, context, "Привет!")
        await send_text(update, context, "Вы написали ..." + update.message.text)

        # await send_text_buttons(update, context, "Запустить процесс?", {
        #                                      "start": "Запустить",
        #                                      "stop": "Остановить",
        # })

# Создаем Telegram-бота
app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
# Подключаем обработчик ошибок
app.add_error_handler(error_handler)

session.mode = None
session.image_type = 'create_anime'

# Регистрируем (подключаем) созданные функции
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("image", create_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
app.add_handler(CallbackQueryHandler(create_button, pattern='^create_.*'))
app.run_polling()
