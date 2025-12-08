from telegram.ext import ApplicationBuilder, MessageHandler, filters, CallbackQueryHandler, CommandHandler
import os
from ai import *
from util import *


# тут будем писать наш код :)
async def hello(update, context):
    await send_text(update, context, "Привет!")
    await send_text(update, context, "Как дела, *дружище*?")
    await send_text(update, context, "Ты написал ..." + update.message.text)

    await send_text_buttons(update, context, "Запустить процесс?", {
                                             "start": "Запустить",
                                             "stop": "Остановить",
    })

async def hello_button(update, context):
    query = update.callback_query.data

    if query == "start":
        await send_text(update, context, "Процесс запущен!")
    else:
        await send_text(update, context, "Процесс остановлен!")


# Создаем Telegram-бота
app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
# Регистрируем (подключаем) созданные функции
app.add_handler(MessageHandler(filters.TEXT, hello))
app.add_handler(CallbackQueryHandler(hello_button))
app.run_polling()
