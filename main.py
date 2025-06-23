from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import openai
import os
from dotenv import load_dotenv
from util import (
    send_photo, send_text, load_message, load_prompt,
    show_main_menu, Dialog
)
from gpt_service.gpt import gpt, gpt_dialog
from bot_service.random_facts import get_random_fact
from bot_service.talk import talk, talk_dialog, load_character_prompt
from bot_service.shared import dialog, chatgpt
from bot_service.quiz import (
    quiz_command, quiz_start, topic_selected,
    handle_quiz_answer, handle_quiz_callback,
    SELECTING_TOPIC, ANSWERING_QUESTION
)
from bot_service.business_ideas import (
    business_command, business_start, category_selected,
    handle_business_callback, SELECTING_CATEGORY, GENERATING_IDEA
)

import requests
from io import BytesIO
import httpx

from telegram import InputMediaPhoto

# Загружаем переменные окружения
load_dotenv()

# Проверяем наличие необходимых переменных окружения
required_env_vars = ["TG_BOT_TOKEN", "CHATGPT_TOKEN"]
missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Отсутствуют необходимые переменные окружения: {', '.join(missing_vars)}")



# Инициализируем приложение Telegram
try:
    application = Application.builder().token(os.getenv("TG_BOT_TOKEN")).build()
except Exception as e:
    raise RuntimeError(f"Ошибка при инициализации Telegram бота: {e}")

async def start(update, context):
    """Обработчик команды /start"""
    dialog.mode = "main"
    text = load_message("main")
    await send_photo(update, context, "main")
    await send_text(update, context, text)
    await show_main_menu(update, context, {
        "start": "главное меню бота",
        "gpt": "задать вопрос чату GPT 🧠",
        "talk": "переписка со звездами 😈",
        "fact": "рандомный факт",
        "quiz": "проверь свои знания 🎯",
        "business": "генератор идей для бизнеса 💡"
    })

async def talk_button(update, context):
    """Обработчик кнопки диалога с личностями"""
    query = update.callback_query
    await query.answer()
    await send_photo(update, context, query.data)
    await send_text(update, context, "отличный выбор! Можете начать общаться!")
    prompt = load_character_prompt(query.data)
    chatgpt.set_prompt(prompt)

async def random_fact(update, context):
    """Обработчик команды случайного факта"""
    fact = get_random_fact()
    await send_photo(update, context, "facts")
    await send_text(update, context, f"📚 Интересный факт:\n\n{fact}")

async def business_button(update, context):
    """Обработчик кнопки генератора идей"""
    query = update.callback_query
    await query.answer()
    return await business_start(update, context)

# Создаем обработчики для квиза
quiz_handler = ConversationHandler(
    entry_points=[
        CommandHandler('quiz', quiz_command),
        CallbackQueryHandler(quiz_start, pattern='^quiz_interface$')
    ],
    states={
        SELECTING_TOPIC: [
            CallbackQueryHandler(topic_selected, pattern=r'^quiz_topic_'),
            CallbackQueryHandler(handle_quiz_callback, pattern=r'^quiz_')
        ],
        ANSWERING_QUESTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quiz_answer),
            CallbackQueryHandler(handle_quiz_callback, pattern=r'^quiz_')
        ]
    },
    fallbacks=[
        CommandHandler('quiz', quiz_command),
        CallbackQueryHandler(quiz_start, pattern='^quiz_interface$')
    ],
    per_chat=True,
    name="quiz_conversation"
)

# Создаем обработчики для генератора идей
business_handler = ConversationHandler(
    entry_points=[
        CommandHandler('business', business_command),
        CallbackQueryHandler(business_start, pattern='^business_interface$')
    ],
    states={
        SELECTING_CATEGORY: [
            CallbackQueryHandler(category_selected, pattern=r'^business_category_'),
            CallbackQueryHandler(handle_business_callback, pattern=r'^business_'),
            CallbackQueryHandler(handle_business_callback, pattern=r'^main_menu$')
        ],
        GENERATING_IDEA: [
            CallbackQueryHandler(handle_business_callback, pattern=r'^business_'),
            CallbackQueryHandler(handle_business_callback, pattern=r'^main_menu$')
        ]
    },
    fallbacks=[
        CommandHandler('business', business_command),
        CallbackQueryHandler(business_start, pattern='^business_interface$')
    ],
    per_chat=True,
    name="business_conversation"
)

# Добавляем обработчики в правильном порядке
# Сначала добавляем ConversationHandler'ы
application.add_handler(business_handler)
application.add_handler(quiz_handler)

# Затем добавляем обработчики команд
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("gpt", gpt))
application.add_handler(CommandHandler("talk", talk))
application.add_handler(CommandHandler("fact", random_fact))
application.add_handler(CommandHandler("business", business_command))

# Добавляем обработчики для диалогов
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, talk_dialog))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, gpt_dialog))

# Добавляем обработчики для кнопок
application.add_handler(CallbackQueryHandler(talk_button, pattern="^talk_.*"))
application.add_handler(CallbackQueryHandler(business_button, pattern="^business_interface$"))

# Запускаем бота
if __name__ == '__main__':
    application.run_polling(allowed_updates=Update.ALL_TYPES)

