
import json
import os
import re
import subprocess
from pathlib import Path

import openai
import requests
from dotenv import load_dotenv
from PySide6.QtCore import QThread, Signal

from src.utils.BasicUtils import global_signals
from src.utils.logger import logger

PROMPT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "prompts"
    / "basic_prompt.md"
)

RESERVE_PROMPT = """Ты - ассистент для управления ОС.
Твоя задача - распознавать намерения пользователя и выдавать структурированный JSON с действием и параметрами.
Ты вовзращаешь:
{
    "message": "Текст для пользователя",
    "tasks": [
        {
            "action": "название_действия",  # Например: open, close, answer, search
            "function": "название_функции"
            "params": {
                "название_параметра": "значение"}  # Параметры зависят от действия
}
"""

class IntentHandler:
    def __init__(self, offline_model="qwen2.5:3b", api_key = None, online_model = "openrouter/auto", base_url = "https://openrouter.ai/api/v1"):
        """Инициализация обработчика намерений"""
        load_dotenv()
        self.ollama_url = "http://localhost:11434/api/generate"
        self.offline_model = offline_model
        self.base_url = base_url
        self.online_model = online_model
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.online_client = openai.OpenAI(api_key=self._api_key, base_url=self.base_url)
        self.basic_prompt = self._load_prompt()
        logger("IntentHandler", "INFO", f"Расположение промта: {PROMPT_PATH}")
        logger("IntentHandler", "INFO", f"Инициализирован с моделью: {self.offline_model}")
    
    def _load_prompt(self, path=PROMPT_PATH) -> str:
        path = Path(path)
        if not path.exists():
            logger(
                "IntentHandler",
                "WARNING",
                f"Файл промпта не найден, используется встроенный: {path}",
            )
            return RESERVE_PROMPT

        try:
            with path.open("r", encoding="utf-8") as f:
                prompt = f.read()
            logger("IntentHandler", "INFO", f"Промпт загружен из {path}")
            return prompt or RESERVE_PROMPT
        except OSError as e:
            logger("IntentHandler", "ERROR", f"Ошибка чтения промпта: {e}")
            return RESERVE_PROMPT
        
    
    def update_api_key(self, new_key: str):
        """Обновляет API ключ для онлайн-запросов"""
        self._api_key = new_key
        self.online_client = openai.OpenAI(api_key=self._api_key, base_url=self.base_url)
        logger("IntentHandler", "INFO", "API ключ обновлен")
    
    def build_user_data(self, name: str= "", birthday: str = "", gender: str = "", 
                        chat_history: str = "", current_app: str= "", available_apps: list = []) -> str:
        """Генерирует единую строку контекста"""
        return (
            f"ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:\n"
            f"Имя: {name}, Рождение: {birthday}, Пол: {gender}\n"
            f"Текущее окружение: {current_app}\n\n"
            f"Доступные приложения(системные названия): {available_apps}\n\n"
            f"ПОСЛЕДНИЕ СООБЩЕНИЯ:{chat_history}"
        )
    
    def send_request(self, user_text: str, user_data: str = "", use_online: bool = False) -> dict:
        """Отправляет чистый запрос в Ollama и возвращает ответ"""
        prompt = self.basic_prompt + "\n\nСообщение пользователя: " + user_text
        if user_data:
            prompt += "\n\nДанные пользователя: " + user_data
        
        if use_online:
            logger("IntentHandler", "INFO", "Отправлен онлайн-запрос")
            return self._send_online_request(prompt, self.online_model)
        else:
            logger("IntentHandler", "INFO", "Отправлен офлайн-запрос")
            return self._send_offline_request(prompt, self.offline_model )
    
    def _send_offline_request(self, prompt, model) -> dict:
        """Отправляет запрос в Ollama"""
        payload = {
            "model": self.offline_model,
            "prompt": prompt,
            "stream": False,  # Ждем полный ответ, а не поток по буквам
            "format": "json"  # Просим Ollama сразу отдавать JSON
    
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=15)
            if response.status_code == 200:
                raw_response = response.json().get('response')
                
                # Используем безопасный парсинг
                data = IntentHandler.parse_ai_json(raw_response)
                
                if data:
                    global_signals.intent_recognized.emit(data)
                    return data
                else:
                    logger("IntentHandler", "ERROR", "Не удалось распарсить JSON")
                    return {"message": "Ошибка формата", "action": "error"}
            
            return None

        except requests.exceptions.ConnectionError:
            logger("IntentHandler", "ERROR", "Ollama не запущена! Проверьте, что она запущена")
            return None
        except Exception as e:
            logger("IntentHandler", "ERROR", f"Непредвиденная ошибка: {e}")
            return None
    
    def _send_online_request(self, prompt, model="openrouter/auto") -> dict:
        """Отправляет запрос онлайн-модели"""
        try:
            online_model = model
            response = self.online_client.chat.completions.create(
                model=online_model, 
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            logger("IntentHandler", "INFO", f"Онлайн-модель ответила. Модель: {online_model}")
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger("IntentHandler", "ERROR", f"Online API error: {e}")
            logger("IntentHandler", "ERROR", "Проверьте API ключ и доступ к интернету")
            logger("IntentHandler", "INFO", "Запускаю оффлайн модель")
            return self._send_offline_request(prompt, self.offline_model)
    
    def parse_ai_json(raw_response) -> dict:
        """
        Пытается извлечь JSON из строки, даже если модель добавила лишний текст
        """
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # 2. Если ошибка, ищем блок кода через регулярку
            match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    return None
        return None
    
    def shutdown_ollama(self):
        """Полная выгрузка модели из памяти"""
        try:

            unload_payload = {
                "model": self.offline_model,
                "keep_alive": 0
            }
            requests.post("http://localhost:11434/api/generate", json=unload_payload)
            logger("CORE", "INFO", "Модель Ollama выгружена из памяти")
            
        except Exception as e:
            print(f"Ошибка при закрытии Ollama: {e}")

    def start_ollama(self):
        """Запускает Ollama, если он не запущен"""
        try:
            # Проверяем, запущен ли процесс, если нет - стартуем (только для Windows)
            subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            logger("CORE", "INFO", "Ollama serve запущен")
        except: pass

class IntentWorker(QThread):
    # Сигнал, который передаст словарь с результатом обратно в Core
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, handler, user_text, user_data="", use_online=False):
        
        super().__init__()
        self.handler = handler
        self.user_text = user_text
        self.user_data = user_data
        self.use_online = use_online

    def run(self):
        try:
            # Вызываем твой существующий метод send_request
            result = self.handler.send_request(self.user_text, self.user_data, self.use_online)
            if result:
                self.finished.emit(result)
            else:
                self.error.emit("Пустой ответ от ИИ")
        except Exception as e:
            self.error.emit(str(e))