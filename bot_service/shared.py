"""
Общие объекты и сервисы для работы Telegram-бота (диалог и ChatGPT).
"""

import os

from util import Dialog
from gpt_service.gpt_class import ChatGptService


dialog = Dialog()  # Экземпляр диалога для взаимодействия с пользователем
chatgpt = ChatGptService(os.getenv("CHATGPT_TOKEN"))  # Сервис для работы с ChatGPT