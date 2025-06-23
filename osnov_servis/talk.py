from util import Dialog, send_photo, send_text, send_text_buttons, load_message, load_prompt, send_html
from osnov_servis.shared import dialog, chatgpt
import json
import os


def load_character_prompt(character_id: str) -> str:
    """
    Загружает промпт для выбранного персонажа
    :param character_id: ID персонажа (например, 'talk_grande')
    :return: Промпт для персонажа
    """
    character_name = character_id.replace('talk_', '')
    prompt_path = os.path.join('prompts', 'characters', f'{character_name}.txt')

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return f"Ты - {character_name}. Общайся от первого лица, используя характерные фразы и манеру речи."


async def talk(update, context):
    dialog.mode = "talk"
    text = load_message("talk")
    await send_photo(update, context, "talk")
    await send_text_buttons(update, context, text, {
        "talk_grande": "Ариана Гранде 🎵",
        "talk_robbie": "Марго Робби 🎬",
        "talk_zendaya": "Зендея ✨",
        "talk_gosling": "Райан Гослинг 🎭",
        "talk_hardy": "Том Харди 🎪"
    })


async def talk_dialog(update, context):
    text = update.message.text
    my_message = await send_text(update, context, "пишет...")
    answer = await chatgpt.add_message(text)
    await my_message.edit_text(answer)