"""
Модуль для проведения квизов через Telegram-бота с использованием ChatGPT.
"""
import logging
import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from gpt_service.gpt import get_personality_response
from data.quiz_topics import get_quiz_topics_keyboard, get_quiz_topic_data, get_quiz_continue_keyboard

logger = logging.getLogger(__name__)

# Состояния разговора
SELECTING_TOPIC, ANSWERING_QUESTION = range(2)

# Константы для обработки ошибок
ERROR_MESSAGE = "😔 Произошла ошибка. Попробуйте позже или используйте /quiz для перезапуска."


async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка команды /quiz для запуска квиза.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    try:
        logger.info(f'Пользователь {update.effective_user.id} запустил команду /quiz')
        # Очищаем предыдущие данные квиза
        context.user_data.clear()
        return await quiz_start(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке команды /quiz: {e}", exc_info=True)
        await update.message.reply_text(ERROR_MESSAGE)
        return ConversationHandler.END


async def quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начало квиза. Показывает выбор тем и инициализирует счетчики.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    try:
        image_path = "data/images/quiz.png"
        logger.info(f'В квизе используется картинка: {image_path}')
        message_text = (
            "🧠 <b>Квиз - проверь свои знания!</b>\n\n"
            "Выберите тему для квиза:\n\n"
            "💻 <b>Программирование</b> - вопросы о коде и технологиях\n"
            "🏛️ <b>История</b> - исторические факты и события\n"
            "🔬 <b>Наука</b> - физика, химия, биология\n"
            "🌍 <b>География</b> - страны, столицы, природа\n"
            "🎬 <b>Кино</b> - фильмы и актеры\n\n"
            "Выберите тему:"
        )

        keyboard = get_quiz_topics_keyboard()

        # Инициализируем счетчики
        context.user_data['quiz_score'] = 0
        context.user_data['quiz_total'] = 0

        if update.callback_query:
            if os.path.exists(image_path):
                await update.callback_query.message.delete()
                with open(image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=update.callback_query.message.chat_id,
                        photo=photo,
                        caption=message_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
            else:
                await update.callback_query.edit_message_text(
                    message_text,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            await update.callback_query.answer()

        else:
            if os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=message_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
            else:
                await update.message.reply_text(
                    message_text,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )

        return SELECTING_TOPIC

    except Exception as e:
        logger.error(f"Ошибка при запуске квиза: {e}")
        error_text = "😔 Произошла ошибка при запуске квиза. Попробуйте позже."

        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

        return ConversationHandler.END


async def topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка выбора темы квиза пользователем.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    query = update.callback_query
    await query.answer()

    try:
        topic_key = query.data.replace("quiz_topic_", "")
        topic_data = get_quiz_topic_data(topic_key)

        if not topic_data:
            if query.message.photo:
                await query.edit_message_caption("❌ Ошибка: тема не найдена.")
            else:
                await query.edit_message_text("❌ Ошибка: тема не найдена.")
            return ConversationHandler.END

        context.user_data['current_quiz_topic'] = topic_key
        context.user_data['quiz_topic_data'] = topic_data
        processing_text = f"{topic_data['emoji']} Генерирую вопрос по теме {topic_data['name']}... ⏳"
        if query.message.photo:
            await query.edit_message_caption(processing_text, parse_mode='HTML')
        else:
            await query.edit_message_text(processing_text, parse_mode='HTML')

        question = await get_personality_response("Создай вопрос для квиза", topic_data['prompt'])
        if not question:
            raise Exception("Не удалось получить вопрос от GPT")

        context.user_data['current_question'] = question
        correct_answer = extract_correct_answer(question)
        context.user_data['correct_answer'] = correct_answer

        message_text = (
            f"{topic_data['emoji']} <b>Квиз: {topic_data['name']}</b>\n\n"
            f"{question}\n\n"
            f"📊 <b>Счет:</b> {context.user_data['quiz_score']}/{context.user_data['quiz_total']}\n\n"
            "✍️ Напишите ваш ответ (A, B, C или D):"
        )

        if query.message.photo:
            await query.edit_message_caption(
                caption=message_text,
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                text=message_text,
                parse_mode='HTML'
            )

        return ANSWERING_QUESTION

    except Exception as e:
        logger.error(f"Ошибка при выборе темы квиза: {e}")
        try:
            if query.message.photo:
                await query.edit_message_caption("😔 Произошла ошибка при генерации вопроса. Попробуйте еще раз.")
            else:
                await query.edit_message_text("😔 Произошла ошибка при генерации вопроса. Попробуйте еще раз.")
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="😔 Произошла ошибка при генерации вопроса. Попробуйте еще раз."
            )
        return ConversationHandler.END


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка ответа пользователя на вопрос квиза.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    try:
        user_answer = update.message.text.strip().upper()
        if user_answer not in ['A', 'B', 'C', 'D']:
            await update.message.reply_text(
                "❌ Пожалуйста, введите только одну букву: A, B, C или D"
            )
            return ANSWERING_QUESTION

        correct_answer = context.user_data.get('correct_answer', '').upper()
        topic_data = context.user_data.get('quiz_topic_data')
        current_question = context.user_data.get('current_question', '')

        if not topic_data or not correct_answer:
            await update.message.reply_text(
                "❌ Произошла ошибка: данные квиза не найдены. Используйте /quiz для начала."
            )
            return ConversationHandler.END

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        is_correct = user_answer == correct_answer

        # Обновляем счетчик
        context.user_data['quiz_total'] += 1
        if is_correct:
            context.user_data['quiz_score'] += 1

        # Отправляем сообщение о том, что проверяем ответ
        processing_msg = await update.message.reply_text(
            f"{topic_data['emoji']} Проверяю ответ... ⏳"
        )

        # Получаем детальный анализ ответа от ChatGPT
        analysis_prompt = f"""Пользователь ответил '{user_answer}' на вопрос:
        {current_question}

        Правильный ответ: {correct_answer}

        Дай краткое объяснение (2-3 предложения), почему ответ правильный или неправильный, и интересный факт по теме."""

        detailed_response = await get_personality_response(analysis_prompt,
                                                           "Ты эксперт по квизам, объясняешь ответы понятно и интересно.")

        # Формируем результат
        if is_correct:
            result_text = f"✅ <b>Правильно!</b>\n\n{detailed_response}"
        else:
            result_text = f"❌ <b>Неправильно!</b>\n\nПравильный ответ: <b>{correct_answer}</b>\n\n{detailed_response}"

        # Кнопки для продолжения
        keyboard = get_quiz_continue_keyboard(context.user_data['current_quiz_topic'])

        # Удаляем сообщение об обработке и отправляем результат
        await processing_msg.delete()
        await update.message.reply_text(
            f"{topic_data['emoji']} <b>Результат квиза</b>\n\n"
            f"{result_text}\n\n"
            f"📊 <b>Ваш счет:</b> {context.user_data['quiz_score']}/{context.user_data['quiz_total']}",
            parse_mode='HTML',
            reply_markup=keyboard
        )

        return ANSWERING_QUESTION

    except Exception as e:
        logger.error(f"Ошибка при обработке ответа квиза: {e}")
        await update.message.reply_text(
            "😔 Произошла ошибка при проверке ответа. Попробуйте еще раз."
        )
        return ANSWERING_QUESTION


async def handle_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка нажатий кнопок в квизе.
    :param update: Объект обновления Telegram
    :param context: Контекст Telegram
    :return: Следующее состояние или завершение разговора
    """
    query = update.callback_query
    await query.answer()

    try:
        if query.data.startswith("quiz_continue_"):
            # Продолжаем с той же темой
            topic_key = query.data.replace("quiz_continue_", "")
            context.user_data['current_quiz_topic'] = topic_key
            context.user_data['quiz_topic_data'] = get_quiz_topic_data(topic_key)

            # Генерируем новый вопрос
            topic_data = context.user_data['quiz_topic_data']
            processing_text = f"{topic_data['emoji']} Генерирую вопрос по теме {topic_data['name']}... ⏳"

            if query.message.photo:
                await query.edit_message_caption(processing_text, parse_mode='HTML')
            else:
                await query.edit_message_text(processing_text, parse_mode='HTML')

            question = await get_personality_response("Создай вопрос для квиза", topic_data['prompt'])
            if not question:
                raise Exception("Не удалось получить вопрос от GPT")

            context.user_data['current_question'] = question
            correct_answer = extract_correct_answer(question)
            context.user_data['correct_answer'] = correct_answer

            message_text = (
                f"{topic_data['emoji']} <b>Квиз: {topic_data['name']}</b>\n\n"
                f"{question}\n\n"
                f"📊 <b>Счет:</b> {context.user_data['quiz_score']}/{context.user_data['quiz_total']}\n\n"
                "✍️ Напишите ваш ответ (A, B, C или D):"
            )

            if query.message.photo:
                await query.edit_message_caption(
                    caption=message_text,
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text(
                    text=message_text,
                    parse_mode='HTML'
                )

            return ANSWERING_QUESTION

        elif query.data == "quiz_change_topic":
            return await quiz_start(update, context)

        elif query.data == "quiz_finish":
            # Показываем финальный результат
            score = context.user_data.get('quiz_score', 0)
            total = context.user_data.get('quiz_total', 0)

            if total > 0:
                percentage = round((score / total) * 100)
                if percentage >= 80:
                    emoji = "🏆"
                    grade = "Отлично!"
                elif percentage >= 60:
                    emoji = "🥈"
                    grade = "Хорошо!"
                elif percentage >= 40:
                    emoji = "🥉"
                    grade = "Неплохо!"
                else:
                    emoji = "📚"
                    grade = "Есть куда расти!"
            else:
                percentage = 0
                emoji = "🤔"
                grade = "Попробуйте еще раз!"

            final_text = (
                f"{emoji} <b>Квиз завершен!</b>\n\n"
                f"📊 <b>Финальный результат:</b>\n"
                f"Правильных ответов: {score} из {total}\n"
                f"Процент: {percentage}%\n\n"
                f"<b>{grade}</b>\n\n"
                "Спасибо за участие! 🎉"
            )

            # Очищаем данные квиза
            context.user_data.clear()

            # Создаем кнопки главного меню
            keyboard = [

                [InlineKeyboardButton("🧠 Квиз", callback_data="quiz_interface")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем финальное сообщение с кнопками
            await query.edit_message_text(
                final_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )

            # Завершаем разговор
            return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка в quiz callback: {e}")
        await query.edit_message_text("😔 Произошла ошибка. Попробуйте еще раз.")
        return ConversationHandler.END

    return ANSWERING_QUESTION


def extract_correct_answer(question_text):
    """
    Извлекает правильный ответ из текста вопроса квиза.
    :param question_text: Текст вопроса
    :return: Буква правильного ответа (A, B, C или D)
    """
    try:
        lines = question_text.split('\n')
        for line in lines:
            if 'правильный ответ' in line.lower():
                match = re.search(r'[ABCD]', line.upper())
                if match:
                    return match.group()

        match = re.search(r'ответ:\s*([ABCD])', question_text.upper())
        if match:
            return match.group(1)

        return 'A'  # Fallback
    except Exception as e:
        logger.error(f"Ошибка при извлечении правильного ответа: {e}")
        return 'A'