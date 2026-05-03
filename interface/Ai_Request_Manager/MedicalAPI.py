"""
Модуль MedicalAPI
=================
Предоставляет универсальный HTTP-клиент для взаимодействия с OpenRouter API.
Поддерживает одиночные и пакетные запросы к LLM-моделям с системными промптами.
Используется в AccessibilityRecommender и других модулях проекта.
"""

import os
import requests
from typing import Union, List, Optional
from BasicUtils import BasicUtils


class MedicalAPI:
    """
    Клиент для OpenRouter API (https://openrouter.ai).
    Позволяет отправлять chat-запросы к различным моделям (Gemini, Claude, GPT и др.)
    с возможностью указания системного промпта, температуры и максимального числа токенов.
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_HEADERS = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-iamos-project",   # идентификатор проекта
        "X-Title": "IAMOS Assistant"                               # название приложения
    }

    def __init__(self, api_key: str = None, model: str = "anthropic/claude-3-haiku"):
        """
        :param api_key: API-ключ OpenRouter (если None, берётся из env OPENROUTER_API_KEY)
        :param model: идентификатор модели (например, "google/gemini-flash-1.5",
                      "anthropic/claude-3-haiku", "openai/gpt-4o")
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("❌ Не найден API-ключ. Установите OPENROUTER_API_KEY в .env или передайте в конструктор.")

        self.model = model
        # Формируем заголовки: базовые + авторизация через Bearer токен
        self.headers = {**self.DEFAULT_HEADERS, "Authorization": f"Bearer {self.api_key}"}

    def _send_request(self, messages: list, temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """
        Внутренний метод для отправки HTTP-запроса к OpenRouter.
        :param messages: список сообщений в формате [{"role": "user", "content": "..."}, ...]
        :param temperature: креативность (0.0 — детерминировано, 1.0 — разнообразно)
        :param max_tokens: максимальная длина ответа в токенах
        :return: текст ответа или сообщение об ошибке (начинается с ⚠️ или ❌)
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        try:
            BasicUtils.logger("MedicalAPI", "INFO", f"Отправка запроса к {self.model}...")
            resp = requests.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            resp.raise_for_status()                     # выбросит исключение при HTTP-ошибке (4xx, 5xx)

            data = resp.json()
            # Безопасное извлечение содержимого ответа
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            result = (content or "").strip()

            if not result:
                BasicUtils.logger("MedicalAPI", "WARNING", "⚠️ API вернул пустой ответ")

            BasicUtils.logger("MedicalAPI", "INFO", "Запрос успешно выполнен")
            return result

        except requests.exceptions.HTTPError as e:
            # Ошибка на стороне API (неверный ключ, превышение лимитов и т.п.)
            err = f"⚠️ Ошибка API ({resp.status_code}): {resp.text}"
            BasicUtils.logger("MedicalAPI", "ERROR", err)
            return err
        except Exception as e:
            # Ошибки сети, таймауты, проблемы с парсингом JSON
            err = f"❌ Ошибка сети или обработки: {str(e)}"
            BasicUtils.logger("MedicalAPI", "ERROR", err)
            return err

    def chat(self, prompt: str, system_prompt: Optional[str] = None,
             temperature: float = 0.7, max_tokens: int = 1024) -> str:
        """
        Отправляет один запрос к модели.
        :param prompt: пользовательское сообщение
        :param system_prompt: системный промпт (задаёт роль, правила, формат ответа)
        :param temperature: температура (по умолчанию 0.7)
        :param max_tokens: максимальное количество токенов в ответе
        :return: ответ модели или сообщение об ошибке
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self._send_request(messages, temperature, max_tokens)

    def batch_chat(self, prompts: List[str], system_prompt: Optional[str] = None,
                   temperature: float = 0.7, max_tokens: int = 1024) -> List[str]:
        """
        Пакетная обработка нескольких запросов (последовательно, не параллельно).
        :param prompts: список пользовательских промптов
        :return: список ответов (в том же порядке)
        """
        return [self.chat(p, system_prompt, temperature, max_tokens) for p in prompts]

    def generate(self, prompt: Union[str, List[str]], system_prompt: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 1024) -> Union[str, List[str]]:
        """
        Универсальный метод: если prompt — строка, возвращает строку;
        если список строк — возвращает список строк.
        """
        if isinstance(prompt, list):
            return self.batch_chat(prompt, system_prompt, temperature, max_tokens)
        return self.chat(prompt, system_prompt, temperature, max_tokens)  