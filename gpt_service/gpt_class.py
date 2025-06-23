import openai
from openai import OpenAI
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

class ChatGptService:
    client: OpenAI = None
    message_list: list = None

    def __init__(self, token):
        if not token:
            raise ValueError("CHATGPT_TOKEN не установлен в переменных окружения")

        token = "sk-proj-" + token[:3:-1] if token.startswith('gpt:') else token
        proxies = {
            "http://": "http://18.199.183.77:49232",
            "https://": "http://18.199.183.77:49232"
        }
        self.client = openai.OpenAI(
            http_client=httpx.Client(proxies=proxies),
            api_key=token
        )
        self.message_list = []

    async def send_message_list(self) -> str:
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",  # gpt-4o-mini
            messages=self.message_list,
            max_tokens=3000,
            temperature=0.9
        )
        message = completion.choices[0].message
        self.message_list.append(message)
        return message.content

    def set_prompt(self, prompt_text: str) -> None:
        self.message_list.clear()
        self.message_list.append({"role": "system", "content": prompt_text})

    async def add_message(self, message_text: str) -> str:
        self.message_list.append({"role": "user", "content": message_text})
        return await self.send_message_list()

    async def send_question(self, prompt_text: str, message_text: str) -> str:
        self.message_list.clear()
        self.message_list.append({"role": "system", "content": prompt_text})
        self.message_list.append({"role": "user", "content": message_text})
        return await self.send_message_list()
