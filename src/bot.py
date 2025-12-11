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
    await hide_main_menu(update, context)

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


async def edit_command(update, context):
    session.mode = 'edit'
    text = load_message(session.mode)
    await send_photo(update, context, session.mode)
    await send_text(update, context, text)


async def edit_message(update, context):
    text = update.message.text
    user_id = update.message.from_user.id
    photo_path = f'resources/users/{user_id}/photo.jpg'

    if not os.path.exists(photo_path):
        await send_text(update, context, "Сначала загрузите илисоздайте картинку")
        return

    prompt = load_prompt(session.mode)
    ai_edit_image(
        input_image_path=photo_path,
        prompt=prompt + text,
        output_path=photo_path
    )
    await send_photo(update, context, photo_path)


async def save_photo(update, context):
    photo = update.message.photo[-1]

    file = await context.bot.get_file(photo.file_id)
    user_id = update.message.from_user.id
    photo_path = f'resources/users/{user_id}/photo.jpg'
    await file.download_to_drive(photo_path)

    await send_text(update, context, "Фото подготовлено к работе")


async def merge_command(update, context):
    session.mode = 'merge'
    session.image_list.clear()
    text = load_message(session.mode)
    await send_photo(update, context, session.mode)
    await send_text_buttons(update, context, text, {
        "merge_join": "Просто объединить картинки",
        "merge_first": "Добавить всех на первую картинку",
        "merge_last": "Добавить всех на последнюю картинку",
    })


async def merge_add_photo(update, context):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)

    image_count = len(session.image_list) + 1

    user_id = update.message.from_user.id

    photo_path = f'resources/users/{user_id}/photo{image_count}.jpg'
    await file.download_to_drive(photo_path)

    session.image_list.append(photo_path)

    await send_text(update, context, f"{image_count} фото подготовлено к работе")


async def merge_button(update, context):
    await update.callback_query.answer()
    query = update.callback_query.data
    user_id = update.callback_query.from_user.id
    result_path = f'resources/users/{user_id}/result.jpg'

    image_count = len(session.image_list)
    if image_count < 2:
        await send_text(update, context, "Сначала загрузите ваши фото")
        return

    prompt = load_prompt(query)
    ai_merge_image(
            input_image_path_list=session.image_list,
            prompt=prompt,
            output_path=result_path
    )
    await send_photo(update, context, result_path)


async def party_command(update, context):
    session.mode = 'party'
    text = load_message(session.mode)

    await send_photo(update, context, session.mode)

    await  send_text_buttons(update, context, text, {
        "party_image1": "🐺 Лунное затмение (оборотень)",
        "party_image2": "🦇 Проклятое зеркало (вампир)",
        "party_image3": "🔮 Ведьмин круг (дым и руны)",
        "party_image4": "🧟 Гниение времени (зомби)",
        "party_image5": "😈 Призыв демона (демон)",
    })


async def on_message(update, context):
    if session.mode == 'create':
        await create_message(update, context)
    elif session.mode == 'edit':
        await edit_message(update, context)
    else:
        await send_text(update, context, "Привет!")
        await send_text(update, context, "Вы написали ..." + update.message.text)


async def on_photo(update, context):
    if session.mode == 'merge':
        await merge_add_photo(update, context)
    else:
        await save_photo(update, context)


# Создаем Telegram-бота
app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
# Подключаем обработчик ошибок
app.add_error_handler(error_handler)

session.mode = None
session.image_type = 'create_anime'
session.image_list = []

# Регистрируем (подключаем) созданные функции
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("image", create_command))
app.add_handler(CommandHandler("edit", edit_command))
app.add_handler(CommandHandler("merge", merge_command))
app.add_handler(CommandHandler("party", party_command))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, on_photo))

app.add_handler(CallbackQueryHandler(create_button, pattern='^create_.*'))
app.add_handler(CallbackQueryHandler(merge_button, pattern='^merge_.*'))

app.run_polling()
