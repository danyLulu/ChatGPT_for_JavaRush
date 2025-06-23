"""
Модуль для генерации бизнес-идей с помощью Telegram-бота и ChatGPT.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from gpt_service.gpt import get_personality_response

logger = logging.getLogger(__name__)

# Состояния разговора
SELECTING_CATEGORY, GENERATING_IDEA = range(2)

# Категории бизнеса
BUSINESS_CATEGORIES = {
    'online': {
        'name': '🌐 Онлайн-бизнес',
        'prompt': 'Создай идею для онлайн-бизнеса. Включи описание, целевую аудиторию, примерную стоимость запуска и потенциальные риски.'
    },
    'retail': {
        'name': '🏪 Розничная торговля',
        'prompt': 'Создай идею для розничного бизнеса. Включи описание, локацию, целевую аудиторию, примерную стоимость запуска и потенциальные риски.'
    },
    'service': {
        'name': '🔧 Сфера услуг',
        'prompt': 'Создай идею для бизнеса в сфере услуг. Включи описание, целевую аудиторию, примерную стоимость запуска и потенциальные риски.'
    },
    'food': {
        'name': '🍽️ Ресторанный бизнес',
        'prompt': 'Создай идею для ресторанного бизнеса. Включи концепцию, меню, целевую аудиторию, примерную стоимость запуска и потенциальные риски.'
    }
}


def get_business_categories_keyboard():
    """
    Создает клавиатуру с категориями бизнеса для Telegram-бота.
    :return: InlineKeyboardMarkup с кнопками категорий
    """
    keyboard = []
    for category_id, category_data in BUSINESS_CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(
            category_data['name'],
            callback_data=f"business_category_{category_id}"
        )])
    return InlineKeyboardMarkup(keyboard)


def get_business_continue_keyboard():
    """
    Создает клавиатуру для продолжения генерации идеи или возврата в главное меню.
    :return: InlineKeyboardMarkup с кнопками
    """
    keyboard = [
        [InlineKeyboardButton("🔄 Новая идея", callback_data="business_new_idea")],
        [InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def business_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка команды /business для запуска генератора бизнес-идей.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    try:
        logger.info(f'Пользователь {update.effective_user.id} запустил команду /business')
        return await business_start(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /business: {e}", exc_info=True)
        await update.message.reply_text("😔 Произошла ошибка. Попробуйте позже.")
        return ConversationHandler.END


async def business_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начало генерации бизнес-идеи. Показывает выбор категорий.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    try:
        message_text = (
            "💡 <b>Генератор идей для бизнеса</b>\n\n"
            "Выберите категорию бизнеса, для которой хотите получить идею:\n\n"
            "🌐 <b>Онлайн-бизнес</b> - интернет-магазины, сервисы, контент\n"
            "🏪 <b>Розничная торговля</b> - магазины, торговые точки\n"
            "🔧 <b>Сфера услуг</b> - консультации, ремонт, обучение\n"
            "🍽️ <b>Ресторанный бизнес</b> - кафе, рестораны, фуд-корты\n\n"
            "Выберите категорию:"
        )

        keyboard = get_business_categories_keyboard()

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            await update.callback_query.answer()
        else:
            await update.message.reply_text(
                message_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )

        return SELECTING_CATEGORY

    except Exception as e:
        logger.error(f"Ошибка при запуске генератора идей: {e}")
        error_text = "😔 Произошла ошибка. Попробуйте позже."

        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

        return ConversationHandler.END


async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка выбора категории бизнеса пользователем.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    query = update.callback_query
    await query.answer()

    try:
        category_id = query.data.replace("business_category_", "")
        category_data = BUSINESS_CATEGORIES.get(category_id)

        if not category_data:
            await query.edit_message_text("❌ Ошибка: категория не найдена.")
            return ConversationHandler.END

        context.user_data['current_category'] = category_id
        context.user_data['category_data'] = category_data

        processing_text = f"💭 Генерирую идею для {category_data['name']}... ⏳"
        await query.edit_message_text(processing_text, parse_mode='HTML')

        # Получаем идею от GPT
        idea = await get_personality_response(
            "Создай детальную бизнес-идею",
            category_data['prompt']
        )

        if not idea:
            raise Exception("Не удалось получить идею от GPT")

        # Форматируем и отправляем результат
        result_text = (
            f"💡 <b>Идея для {category_data['name']}</b>\n\n"
            f"{idea}"
        )

        keyboard = get_business_continue_keyboard()
        await query.edit_message_text(
            result_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )

        return GENERATING_IDEA

    except Exception as e:
        logger.error(f"Ошибка при генерации идеи: {e}")
        await query.edit_message_text("😔 Произошла ошибка при генерации идеи. Попробуйте еще раз.")
        return ConversationHandler.END


async def handle_business_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка нажатий кнопок в генераторе бизнес-идей.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    query = update.callback_query
    await query.answer()

    try:
        if query.data == "business_new_idea":
            # Очищаем предыдущие данные
            context.user_data.clear()
            return await business_start(update, context)

        elif query.data == "main_menu":
            # Очищаем данные
            context.user_data.clear()

            # Создаем кнопки главного меню
            keyboard = [
                [InlineKeyboardButton("🧠 Квиз", callback_data="quiz_interface")],
                [InlineKeyboardButton("💡 Генератор идей", callback_data="business_interface")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем сообщение с главным меню
            await query.edit_message_text(
                "🏠 <b>Главное меню</b>\n\nВыберите действие:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            return ConversationHandler.END

        elif query.data.startswith("business_category_"):
            # Если пользователь нажал на категорию из главного меню
            return await category_selected(update, context)

    except Exception as e:
        logger.error(f"Ошибка в business callback: {e}")
        await query.edit_message_text("😔 Произошла ошибка. Попробуйте еще раз.")
        return ConversationHandler.END

    return GENERATING_IDEA