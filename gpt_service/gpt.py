from util import send_photo, send_text, load_message, load_prompt
from bot_service.shared import dialog, chatgpt
import logging

logger = logging.getLogger(__name__)

WAITING_FOR_MESSAGE = 1


async def gpt(update, context):
    dialog.mode = "gpt"
    text = load_message("gpt")
    await send_photo(update, context, "gpt")
    await send_text(update, context, text)
    # Устанавливаем промпт для GPT
    chatgpt.set_prompt(load_prompt("gpt"))


async def gpt_dialog(update, context):
    if dialog.mode != "gpt":
        return

    text = update.message.text

    # Показываем сообщение о генерации
    my_message = await send_text(update, context,
                                 "ChatGPT генерирует информацию. Это может занять несколько секунд...")

    try:
        # Получаем ответ от GPT
        answer = await chatgpt.add_message(text)
        await my_message.edit_text(answer)
    except Exception as e:
        logger.error(f"Error in GPT dialog: {e}")
        await my_message.edit_text("Извините, произошла ошибка при генерации ответа. Попробуйте еще раз.")


async def get_personality_response(prompt: str, system_prompt: str = None) -> str:
    """
    Получает ответ от ChatGPT с учетом личности.

    Args:
        prompt (str): Запрос пользователя
        system_prompt (str, optional): Системный промпт для определения личности

    Returns:
        str: Ответ от ChatGPT
    """
    try:
        if system_prompt:
            chatgpt.set_prompt(system_prompt)
        return await chatgpt.add_message(prompt)
    except Exception as e:
        logger.error(f"Ошибка при получении ответа от ChatGPT: {e}")
        return "Извините, произошла ошибка при обработке запроса."







