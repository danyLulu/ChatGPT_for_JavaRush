import os

from util import Dialog
from gpt_service.gpt_class import ChatGptService


dialog = Dialog()
chatgpt = ChatGptService(os.getenv("CHATGPT_TOKEN"))